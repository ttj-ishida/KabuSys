# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  
安定性と互換性はセマンティックバージョニングに基づいて管理します。

全般的な注意:
- 日付はリリース日を示します。
- このリポジトリは初期リリースとして機能群を実装しています。

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ構成
  - パッケージルート: `kabusys`（`__version__ = "0.1.0"`、公開サブパッケージ: data, strategy, execution, monitoring）。
- 環境変数・設定管理 (`kabusys.config`)
  - .env 自動ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
  - 読み込み優先度: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env のパース機能を実装（コメント、シングル/ダブルクォート、エスケープ、`export KEY=val` 形式に対応）。
  - 環境設定を型付きプロパティで提供する `Settings` クラスを実装。主な設定:
    - J-Quants / kabu API / LINE API / DB パス（DuckDB / SQLite） / Paper Trading 設定（`PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`）/監視用ファイルパス（PID/KILL）/閾値（CPU/メモリ/ディスク）/環境モード（development/paper_trading/live）/ログレベル。
  - 設定のバリデーション実装（無効な `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` は ValueError を送出）。

- ニュース NLP（AI）機能 (`kabusys.ai`)
  - `news_nlp.score_news`:
    - 前日15:00 JST〜当日08:30 JST 相当のニュースウィンドウを計算するユーティリティを実装（UTC naive datetime を返す `calc_news_window`）。
    - raw_news と news_symbols を結合して銘柄ごとに最新記事を集約（記事数・文字数の上限でトリム）。
    - 複数銘柄を最大バッチサイズ（デフォルト20）で OpenAI に送信し、JSON Mode のレスポンスを検証して `ai_scores` テーブルへ冪等書き込み（DELETE → INSERT）。
    - API の 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライ実装。
    - レスポンス検証: JSON 抽出、"results" リスト存在確認、コード整合性、スコア数値化、±1.0 クリップ。
    - テスト容易性のため `_call_openai_api` を差し替え可能（unittest.mock.patch 推奨）。
    - API キー注入可能（引数 or 環境変数 `OPENAI_API_KEY`）。未設定時は ValueError を送出。

  - `regime_detector.score_regime`:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（データ不足時は中立扱い）と、マクロニュースの LLM センチメントを重み付け（70% / 30%）して市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタしてタイトルリストを作成し、OpenAI（gpt-4o-mini）で JSON レスポンスとしてセンチメントを取得。
    - API 障害時は macro_sentiment=0.0 のフェイルセーフ。API キーの注入対応（引数または環境変数 `OPENAI_API_KEY`）、未設定では ValueError。
    - レジーム結果を `market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を上位へ伝播。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算モジュール（`factor_research`）:
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: 最新の raw_financials と株価から PER / ROE を計算（EPS が 0/欠損のときは None）。
    - DuckDB SQL を活用した計算実装（prices_daily / raw_financials のみ参照、外部 API にはアクセスしない）。
  - 特徴量探索モジュール（`feature_exploration`）:
    - 将来リターンの一括取得 (`calc_forward_returns`)：任意ホライズン（デフォルト [1,5,21]）に対応し、ホライズン検証（1〜252）を実施。
    - IC（Spearman ρ）計算 (`calc_ic`)：ファクター値と将来リターンのランク相関を計算（有効レコード < 3 の場合は None）。
    - ランク変換ユーティリティ (`rank`)：同順位は平均ランクに処理（丸め対策あり）。
    - ファクター統計サマリー (`factor_summary`)：count/mean/std/min/max/median を計算。
  - `research.__init__` で主要関数を公開。

- データ基盤 / ETL (`kabusys.data`)
  - カレンダー管理 (`calendar_management`):
    - JPX カレンダーを扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得のときは曜日ベース（土日非営業日）でフォールバック。
    - DB 登録値が存在すれば優先し、未登録日は曜日フォールバックで一貫性を保持。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装。J-Quants クライアント経由で差分取得→保存（fetch / save の呼び出しとエラーハンドリング）。バックフィル・健全性チェックを実装。
  - ETL パイプライン (`pipeline`):
    - ETL の結果を表す `ETLResult` データクラスを実装（取得件数・保存件数・品質問題リスト・エラー一覧等）。
    - ETL の設計方針（差分更新、backfill、品質チェックは収集して上位判断に委ねる等）に沿ったインターフェース。
    - `data.etl` で `ETLResult` を再エクスポート。
  - jquants クライアントおよび quality モジュールへの連携ポイントを設置（実装は別モジュールを参照）。

- テスト性・安全性に関する設計上の配慮
  - 日付参照に datetime.today()/date.today() を直接使用しない方針（ルックアヘッドバイアス防止）。target_date を明示的に渡す設計。
  - OpenAI 呼び出し箇所は内部でラップしており、テスト時に差し替え可能。
  - DB 書き込みは冪等性を意識して実装（DELETE→INSERT / ON CONFLICT 方針等）。
  - API 失敗時は極力例外を直ちに上げずフェイルセーフ（ゼロスコアやスキップ）を採用し、処理継続を優先。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

次回以降のCHANGELOGには、API 仕様変更・DB スキーマ変更・既存関数の振る舞い変更（破壊的変更）を明確に記載してください。