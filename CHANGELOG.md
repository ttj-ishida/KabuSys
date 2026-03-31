Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
このプロジェクトの初回リリースをコードから推測して記載しています。

## [Unreleased]

（今後の変更をここに記載します）

## [0.1.0] - 2026-03-31

初回公開リリース（コードベースから推測）。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - public API のエクスポートに data / strategy / execution / monitoring を含む。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする自動ローダーを実装。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に実施（CWD 非依存）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
    - .env パーサは export プレフィックス、クォートされた値、インラインコメント等に対応。
    - 既存 OS 環境変数は保護され、上書きされない実装（protected set）。
  - 設定取得ラッパー `Settings` を提供（`settings` インスタンスを公開）。
    - 必須設定取得時は未設定で例外（ValueError）を送出。
    - デフォルト値（KABUSYS_ENV, LOG_LEVEL, KABU_API_BASE_URL, DB パス等）を提供。
    - env 判定ユーティリティ: `is_live`, `is_paper`, `is_dev`。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して `ai_scores` テーブルへ書き込む。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う）。
  - バッチ処理:
    - 1 API コールあたり最大 20 銘柄（_BATCH_SIZE=20）。
    - 1銘柄あたり最新 10 記事、最大 3000 文字までトリム。
  - JSON Mode を使用し厳密な JSON 出力を想定（レスポンス検証・パース機能を実装）。
  - リトライ/バックオフ:
    - レート制限(429)、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ（最大回数定義あり）。
    - 失敗はフェイルセーフでスキップ（例外を投げず継続）。
  - スコア処理:
    - スコアを ±1.0 にクリップ。
    - 成功した銘柄のみを DELETE→INSERT で置換（部分失敗時に既存データ保護）。
  - テスト容易性:
    - OpenAI 呼び出し関数 `_call_openai_api` をパッチ可能（unittest.mock.patch）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - 計算フロー:
    - ma200_ratio の計算（target_date 未満のデータのみを使用しルックアヘッドを防止）。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出（最大 20 件）。
    - OpenAI（gpt-4o-mini）の JSON モードでマクロセンチメントを取得、失敗時は 0.0 にフォールバック。
    - 合成スコアをクリップし閾値（±0.2）でラベル付け。
    - `market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - 失敗時のフォールバックやリトライ挙動を実装。

- データ ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETL の公開インターフェース `ETLResult`（dataclass）を導入。
    - 取得/保存件数、品質チェック結果、エラーの集約と辞書化メソッドを提供。
  - 差分更新・バックフィル・品質チェックの設計方針を反映（コード内に詳細な実装方針記述）。

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得・保存）。
  - 営業日判定ユーティリティ:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
  - DB にカレンダーデータがない場合は曜日ベース（平日）でフォールバック。DB 登録値優先の一貫した挙動。
  - 最大探索範囲 `_MAX_SEARCH_DAYS` による安全性対策、バックフィル期間、健全性チェック等を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER、ROE を raw_financials と prices_daily から計算（EPS=0 や欠損時は None）。
    - 実装は DuckDB 上の SQL と Python 組合せで完結し、外部 API に依存しない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: スピアマンのランク相関（IC）を計算（無効・サンプル不足時は None）。
    - rank, factor_summary: ランク変換と統計サマリー（count/mean/std/min/max/median）を提供。
  - 研究向けユーティリティの公開（研究用ワークフローをサポート）。

- その他
  - 全体で DuckDB を主要なローカルデータストアとして使用する実装（DuckDB 接続を引数に取る設計）。
  - 各モジュール内で「ルックアヘッドバイアス防止」に注意した日付範囲設計（datetime.today() 等を直接参照しない）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは引数で注入可能（テスト置換容易化）かつ環境変数 `OPENAI_API_KEY` から取得。キー管理自体は外部の責任である旨を想定した設計。

Notes（利用上の注記）
- .env 自動ロードはデフォルトで有効。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化してください。
- OpenAI 呼び出しは JSON mode を期待するため、レスポンスの検証を行っています。API 側の応答仕様変更があった場合はパーサ側の調整が必要です。
- DuckDB の executemany が空リストを許容しないバージョンに対する保護ロジックを含んでいます（空パラメータチェック）。
- 各書き込み操作はトランザクションで冪等性を保つように実装されていますが、DB スキーマ（テーブル定義等）は事前に整備されていることを前提とします。

（以降のバージョンでは大きな変更点・互換性破壊・セキュリティ修正等を明示して追記してください）