# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠して変更履歴を記載します。  
形式: https://keepachangelog.com/ja/1.0.0/

すべての変更は SemVer に従います。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買・データ基盤のコア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`、主要サブパッケージを `__all__` で公開。
- 環境設定 / 設定管理 (`kabusys.config`)
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探す）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パース実装（export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメント処理などに対応）。
  - 必須設定取得用ユーティリティ `_require` と `Settings` クラスを実装。
  - `Settings` による主要設定プロパティ:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`（デフォルト `http://localhost:18080/kabusapi`）
    - LINE Messaging: `line_channel_access_token`, `line_user_id`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 監視関連: `pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`
    - 実行環境 / ログレベルの検証: `env`（許容値: `development`, `paper_trading`, `live`）、`log_level`（許容値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）
    - 環境判定ヘルパー: `is_live`, `is_paper`, `is_dev`
- AI（自然言語処理）モジュール (`kabusys.ai`)
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - ニュース記事をまとめて OpenAI（gpt-4o-mini, JSON Mode）へ送り、銘柄ごとのセンチメントを計算して `ai_scores` テーブルへ書き込む機能を実装（関数: `score_news`）。
    - ニュース集計ウィンドウ: JST で前日 15:00 ～ 当日 08:30（DB 比較用に UTC naive datetime に変換）。
    - バッチ処理 / トークン肥大化対策: 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - リトライ・エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。レスポンスの厳密なバリデーションを実施。
    - レスポンスの JSON パースと検証ロジック実装（未知コードの無視、数値変換、±1.0 クリップなど）。
  - 市場レジーム検知 (`kabusys.ai.regime_detector`)
    - ETF（1321）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（`bull` / `neutral` / `bear`）を計算、`market_regime` テーブルへ冪等書き込み（`score_regime`）。
    - マクロニュース抽出はキーワードベースでタイトルを取得し、OpenAI に JSON 出力を要求してスコア化。
    - LLM 呼び出しは再試行ロジック（最大リトライ、指数バックオフ）を実装。API 失敗時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - ルックアヘッドバイアス防止: target_date 未満のデータのみ参照し、日付の自動参照を行わない設計。
- データ / ETL (`kabusys.data`)
  - ETL 結果データクラスの公開 (`kabusys.data.pipeline.ETLResult`) を `kabusys.data.etl` で再エクスポート。
  - ETL パイプライン基盤 (`kabusys.data.pipeline`)
    - 差分取得、保存（idempotent）、品質チェックのためのユーティリティを用意。`ETLResult` に品質問題・エラーを集約する仕組みを実装。
  - 市場カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間バッチ更新ジョブ (`calendar_update_job`) と営業日判定ロジックを実装。
    - DB にデータがない場合は曜日ベース（土日除外）のフォールバックを一貫して使用。
    - next/prev/get_trading_days / is_trading_day / is_sq_day 等を提供。
    - バックフィルや健全性チェック（過度な未来日付の検出）を実装。
- リサーチ / ファクター解析 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等の計算関数を実装（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照。
    - データ不足時の扱い（None の返却）を明確に定義。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（`calc_forward_returns`）、IC（Spearman）計算（`calc_ic`）、ランク付けユーティリティ（`rank`）、ファクター統計サマリー（`factor_summary`）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。入力バリデーションあり。
- 共通設計上の注意点・安全対策
  - ルックアヘッドバイアス防止を徹底（各モジュールで date.today() 等を直接参照しない設計）。
  - DB 書き込みはできる限り冪等に（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用）。
  - OpenAI 呼び出しは JSON Mode を使い、レスポンス検証を厳格化。
  - API 呼び出しの失敗時は例外を上位に伝える箇所と、フェイルセーフ（中立値で継続）とを適切に使い分け。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 環境変数の読み込みに関する扱い:
  - OS の既存環境変数はデフォルトで保護し、.env/.env.local による上書きを制御する仕組みを導入（protected set）。
  - 必須トークンは `Settings` 経由で取得し、未設定時は早期に ValueError を送出することで誤った実行を防止（例: OpenAI API キー、J-Quants トークン、Kabu API パスワード）。

### 既知の制約 / 注意事項 (Known issues / Notes)
- OpenAI 呼び出しは gpt-4o-mini を想定しており、API レスポンス仕様の変更に対してはパース/検証で保護していますが、将来的に SDK の変更があれば修正が必要です。
- DuckDB に対する一部バインド動作（空の executemany パラメータ等）に依存した回避コードを実装しています。DuckDB のバージョン依存性に注意してください。
- `Settings.env` と `Settings.log_level` は値検証を行うため、設定ミスがあると起動時に例外が発生します。許容値を確認してください。
- calendar / ETL の動作は J-Quants クライアント実装（外部モジュール）に依存するため、J-Quants 側の変化に注意が必要です。

### 互換性 (Compatibility)
- 初回リリースのため後方互換性に関する注記はありません。

---

開発・運用に必要な主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（score_news / score_regime 実行時に必要）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 を設定で .env 自動ロード無効化）

--- 

今後の予定（例）
- モデルやプロンプト改善、追加の品質チェックルール、ETL のスケジューリング連携、モニタリング・アラート機能の強化など。