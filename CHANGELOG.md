# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージの __version__ に合わせています。

注意: 以下の記載は提示されたコードベースからの機能・設計・振る舞いを推測してまとめたものです（実際のコミット履歴ではありません）。

## [Unreleased]

（特に未リリースの差分はありません）

## [0.1.0] - 2026-03-31

初回リリース。以下の主要機能と実装方針を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__` による基本モジュール公開（data, strategy, execution, monitoring）。
  - バージョン: `__version__ = "0.1.0"`。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env / 環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーはコメント・export プレフィックス・クォート/エスケープに対応。
  - 読み込み時の上書き制御（override / protected keys）をサポート。
  - Settings クラスを提供し、以下の設定をプロパティ経由で取得:
    - J-Quants / kabu API / Slack トークン・チャンネル、データベースパス（duckdb/sqlite）、監視用閾値（CPU/メモリ/ディスク）、実行環境（development/paper_trading/live）、ログレベル等。
  - 設定値のバリデーション（有効な env 値、LOG_LEVEL の検証、必須キー未設定時は ValueError を送出）。

- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリングモジュール (`news_nlp`)
    - raw_news + news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信。
    - バッチサイズ・1銘柄あたりの最大記事数・最大文字数を制限してトークン肥大を防止。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ付きリトライ実装。
    - レスポンスの厳密なバリデーション: JSON 抽出、"results" 配列・各要素の code/score チェック、未知コードは無視、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗に強い冪等処理（取得済みコードのみ DELETE→INSERT を実行、DuckDB executemany の注意を考慮）。
    - テスト容易性: OpenAI 呼び出しはモジュール内の _call_openai_api を差し替え可能（unittest.mock.patch）。
    - ニュース収集ウィンドウ計算ユーティリティ `calc_news_window(target_date)` を提供（JST基準の前日15:00〜当日08:30 を UTC naive datetime に変換）。

  - 市場レジーム判定モジュール (`regime_detector`)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）判定。
    - prices_daily と raw_news を参照して ma200_ratio とマクロニュースタイトルを取得。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価。失敗時は 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成ロジック（クリッピング、しきい値）と `market_regime` テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試みエラーを再送出。
    - API 呼び出しでのリトライ/バックオフ処理、レスポンスパース失敗時のロギングとフォールバック挙動。
    - テスト容易性のため OpenAI クライアント生成にキーを注入可能。

- データプラットフォーム (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management`)
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job`（J-Quants API 経由）を実装。バックフィル・健全性チェックを含む。
    - 営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB に登録された calendar を優先し、未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）による無限ループ防止。
    - jquants_client 経由でのフェッチ/保存処理を想定（外部クライアント呼び出しを使用）。

  - ETL / パイプライン (`pipeline`, `etl`)
    - ETLResult データクラスを追加し、ETL 実行結果（フェッチ数・保存数・品質チェック問題・エラー）を集約して出力可能。
    - pipeline モジュールの公開インターフェース（ETLResult の再エクスポート）。
    - ETL の設計方針（差分取得、バックフィル、品質チェックの扱い、id_token 注入によるテスト性向上）を反映した実装構造。

- 研究・因子モジュール (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算する `calc_momentum`。
    - Volatility/Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する `calc_volatility`。
    - Value: raw_financials から最新決算を取得して PER, ROE を計算する `calc_value`（EPS 無効時は None）。
    - DuckDB を用いた SQL 主導の実装で、外部 API へのアクセスは行わない。
    - 計算結果は (date, code) をキーとした dict のリストで返す。

  - 特徴量探索・統計 (`feature_exploration`)
    - 将来リターン計算 `calc_forward_returns`（horizons デフォルト [1,5,21]、入力検証あり）。
    - IC（Information Coefficient）計算 `calc_ic`（スピアマンランク相関、データ数不足時は None）。
    - ランキングユーティリティ `rank`（同順位は平均ランク、丸め処理で ties を抑制）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median を算出）。
    - すべて標準ライブラリのみで実装（pandas 等に依存しない）。

### 変更 (Changed)
- 設計方針（全体）
  - ルックアヘッドバイアス対策: いずれのモジュールも内部で datetime.today() / date.today() を安易に参照せず、呼び出し側から target_date を渡す設計を採用。これにより時系列解析・バックテストでの再現性を確保。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT を想定）して部分失敗時のデータ保護を実現。
  - OpenAI 呼び出しでのレスポンス不正や API 障害は例外化せずフェイルセーフ動作（スコア 0.0 やスキップ）で継続する方針。
  - DuckDB の互換性を考慮し、executemany の空リスト送信回避など実装上の注意点を反映。

### 修正 (Fixed)
- 明示的な「バグ修正」履歴は初回リリースのためなし。ただし以下の堅牢化が含まれる:
  - .env 読み込みでのファイル I/O エラーは警告で処理を継続。
  - OpenAI の APIError 取り扱いで status_code の有無に対応し、将来の SDK 変化に耐性を持たせる。
  - DuckDB から取り出す日付値の型変換ユーティリティを追加して型不整合を防止。

### 既知の制約・注意点
- OpenAI 呼び出しは gpt-4o-mini を想定しており、JSON Mode の出力形式に依存したパーシングを行っている。API の仕様変更やモデル差異でパース失敗が起きる可能性がある。
- J-Quants / kabu 等の外部クライアント（jquants_client、kabu API）に依存する箇所はモック可能な設計にしているが、実動環境では各種 API キー・エンドポイントの設定が必要。
- DuckDB のバージョン差異に起因する挙動（リスト型バインド等）に注意。実装中に回避コードを入れているが、運用時は環境の DuckDB バージョン確認を推奨。

---

参照: Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）