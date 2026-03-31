# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
リリース日はソースコードから推測した作成日を使用しています。

## [0.1.0] - 2026-03-31

### 追加
- 初回公開: KabuSys 日本株自動売買システムのコアライブラリを追加。
  - パッケージのバージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env パーサ実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメント対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護（OS 環境変数を上書きしない仕組み）と override の挙動。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / データベース / システム設定向けプロパティ）。
  - 必須環境変数が未設定の場合は ValueError を発生させる _require 実装。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI 関連 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI (gpt-4o-mini) にバッチ送信し ai_scores テーブルへ書き込む処理を実装。
    - スコアリング時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチサイズ、トークン肥大対策（記事数・文字数制限）、JSON mode でのレスポンス検証、429/ネットワーク/タイムアウト/5xx に対する指数バックオフでのリトライ実装。
    - レスポンスバリデーション（results リスト・code/score 検証・数値クリップ）とフォールバック動作（失敗時はスキップ・部分書き換えで既存データ保護）。
    - 公開関数: score_news(conn, target_date, api_key=None)。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定する実装。
    - prices_daily/raw_news を DuckDB から参照して ma200_ratio とマクロニュースを取得、OpenAI により macro_sentiment を算出。
    - LLM 呼び出し・再試行ロジック、API エラーやパース失敗時のフェイルセーフ（macro_sentiment=0.0）、スコアの合成・クリップ・ラベル付けを実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

  - AI パッケージ公開 (src/kabusys/ai/__init__.py)
    - score_news をエクスポート。

- データモジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得して market_calendar を冪等更新）。
    - 営業日判定ロジックを提供: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - カレンダーデータ未取得時は曜日（平日）ベースのフォールバックを採用。
    - 最大探索範囲やバックフィル、健全性チェック等の保護ロジックを実装。
    - jquants_client を通じた fetch/save 呼び出しに対応。

  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult データクラスを実装（ETL 実行メトリクス・品質問題・エラー集約）。
    - 差分更新・バックフィル・品質チェックを想定したユーティリティ関数群（内部ユーティリティとしてテーブル存在確認や最大日付取得など）。
    - etl.py で ETLResult を再エクスポート。

  - データパッケージの基礎インターフェースを整備（jquants_client との連携を想定）。

- Research（リサーチ）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）等の計算関数を実装。
    - DuckDB 上で SQL を使って計算し、結果を (date, code) キーの辞書リストで返却する API を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - データ不足時の None ハンドリング、ログ出力等を実装。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのランク相関）。
    - ランク変換ユーティリティ rank(values)（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary(records, columns)（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

- パッケージ構成の整備
  - research パッケージの __init__.py で主要関数を再エクスポート。
  - data.etl で ETLResult を公開する簡易インターフェースを追加。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 削除
- （初回リリースのため該当なし）

### 既知の設計方針・注意点（ドキュメント的補足）
- ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照せず、target_date を明示的に受け渡す実装方針を採用。
- OpenAI への呼び出しは JSON mode を利用し、レスポンスの堅牢な検証とフォールバックを行う（API エラーは再試行・重大な問題時は安全側のデフォルトを使用）。
- DuckDB をデータストアとして利用。DB 書き込みは冪等性を考慮（DELETE→INSERT 等）している。
- ETL/カレンダー更新/AI スコアリングは部分失敗に強い設計：一部銘柄のみ失敗しても他のデータを保護して更新する。
- 環境設定は必須キーを明示的に検証するため、未設定時は早期に例外を投げる（運用でのミスを早期発見）。

---

今後のリリースでは、strategy / execution / monitoring の具体的な実装、追加の品質チェック・テストケース、ドキュメント強化、API クライアントの抽象化などを予定してください。必要であれば、この CHANGELOG を対象コミットやリポジトリの追加情報に合わせて更新します。