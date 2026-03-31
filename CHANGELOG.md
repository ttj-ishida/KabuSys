CHANGELOG
=========

すべての注目すべき変更履歴をここに記録します。
フォーマットは Keep a Changelog に準拠しています（安定した API / 振る舞いの記述を優先）。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージルート: src/kabusys/__init__.py にてバージョンと主要サブパッケージ（data, research, ai, execution, strategy, monitoring など想定）を公開。
- 設定管理
  - src/kabusys/config.py
    - .env / .env.local からの自動環境変数読み込み機能を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサーは export 付き行、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどに対応。
    - 既存 OS 環境変数を保護する protected パラメータや override の挙動を実装。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの取得とバリデーションを行う。
    - 必須変数未設定時は ValueError を送出するヘルパーを実装。
- AI 関連（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を算出・ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - バッチサイズ、記事数上限、1銘柄当たり最大文字数などのトークン肥大化対策を実装（_BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode を期待した応答パース・堅牢な JSON 抽出ロジック、レスポンスバリデーションを実装。スコアは ±1.0 にクリップ。
    - レート制限・ネットワーク切断・タイムアウト・5xx に対する指数バックオフリトライを実装。致命的でない場合は失敗をスキップして処理継続（フェイルセーフ）。
    - 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT による置換を行い既存データを保護。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次の市場レジーム（'bull'/'neutral'/'bear'）を判定する機能を実装。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）を返す安全処理を導入（ルックアヘッド防止）。
    - マクロニュース抽出はキーワードマッチでタイトルを選出（最大 N 件）、LLM（gpt-4o-mini）へ投げて JSON で macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - スコア合成・閾値に基づくラベリング（_BULL_THRESHOLD/_BEAR_THRESHOLD）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI クライアント呼び出しは独立関数化され、テストでモック可能。
- データプラットフォーム / ETL
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラスを公開（ETL 実行結果の集約: 取得件数・保存件数・品質問題・エラー列挙など）。
    - 差分取得・バックフィル・品質チェックを想定した設計で、DuckDB を用いた最大日付取得ユーティリティ等を実装（_get_max_date 等）。
    - 市場カレンダー先読みやバックフィル日数の定義を持つ。
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日列挙・SQ判定機能を実装。
    - DB 登録がない場合は曜日ベース（土日非営業）でフォールバックする一貫したロジックを提供。
    - next_trading_day / prev_trading_day は探索最大日数を _MAX_SEARCH_DAYS で制限し、見つからない場合は ValueError を送出して無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新。バックフィル / 健全性チェック（将来日が過度に遠い場合のスキップ）を行う。
- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR/相対 ATR/平均売買代金/出来高比）、Value（PER, ROE）の計算関数を実装。DuckDB のウィンドウ関数を活用して効率的に算出。
    - データ不足時は None を返す設計。ログ出力で対象銘柄数を報告。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意 horizon、デフォルト [1,5,21]）を実装。複数ホライズンを一度のクエリで取得。
    - IC（Spearman の ρ）計算関数を実装（ランクの取り扱いは平均ランク方式で同順位を処理）。
    - 基本統計量（count/mean/std/min/max/median）を計算する factor_summary を実装。
    - 外部依存（pandas 等）を用いず、標準ライブラリ + DuckDB のみで完結するよう設計。
- モジュール再エクスポート
  - research/__init__.py, ai/__init__.py, data/etl.py 等で主要関数とクラスを再エクスポートして使いやすく整理。

Security
- 環境変数周りでは、.env 読み込み時に既存の OS 環境変数を protected として上書きされないよう配慮。

Notes / Design Decisions
- ルックアヘッドバイアス防止: 多くの関数（news のウィンドウ計算、regime 判定、ETL/リサーチ系）で datetime.today()/date.today() を内部参照せず、呼び出し側から target_date を受け取る設計を採用。
- フェイルセーフ: LLM/API 呼び出しの失敗は致命エラーにせずフォールバック（0.0 やスキップ）して処理を継続する方針。
- テスト容易性: OpenAI 呼び出し部分は分離・独立実装し unittest.mock.patch などで差し替え可能にしている。
- DuckDB バージョン互換性: executemany に空リストを渡せない制約等に配慮した実装（空チェックを明示）。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Security
- なし

(補足)
- ソースコードの一部はコメントや docstring で設計方針・注意点を詳述しており、将来的な拡張（発注/実行モジュール、監視/モニタリング連携等）を想定しています。