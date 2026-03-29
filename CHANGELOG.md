# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
このプロジェクトの初期リリース v0.1.0 の変更点をまとめます。

## [0.1.0] - 2026-03-29

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージ公開インターフェースに data / strategy / execution / monitoring を含める（`__all__`）。

- 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの検出は __file__ を起点に `.git` または `pyproject.toml` を探索して行い、パッケージ配布後も機能するよう設計。
  - `.env` の行パース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
  - 必須環境変数取得ヘルパー `_require` を実装。
  - Settings クラスを実装し、以下の設定をプロパティとして公開：
    - J-Quants / kabu / Slack 関連: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト http://localhost:18080/kabusapi）、`SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス: `DUCKDB_PATH`（デフォルト data/kabusys.duckdb）、`SQLITE_PATH`（デフォルト data/monitoring.db）
    - 環境種別・ログレベル検証: `KABUSYS_ENV`（development, paper_trading, live のいずれか）、`LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパープロパティ

- AI（自然言語処理）機能 (`kabusys.ai`)
  - ニュース NLP スコアリング（`kabusys.ai.news_nlp.score_news`）
    - 指定日用のニュース時間ウィンドウ計算 (`calc_news_window`) を実装（JST 基準で前日 15:00 ～ 当日 08:30 を対象、内部は UTC naive datetime）。
    - raw_news / news_symbols から銘柄毎に記事を集約し、1銘柄あたり最大記事数・文字数でトリム。
    - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信し、JSON レスポンスを検証して ai_scores テーブルへ冪等書き込み（DELETE → INSERT）。
    - レート制限(429)・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスのバリデーション、スコア ±1.0 のクリップ、部分失敗時の既存スコア保護（書込みはスコア取得済みコードのみ）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 `_call_openai_api` を patch 可能）。

  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュース抽出のためのキーワード集合を実装（日本語・米国系キーワードを含む）。
    - OpenAI 呼び出しは JSON レスポンスを期待し、失敗時にはマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - look-ahead バイアス対策（target_date 未満のデータのみ使用、datetime.today() を参照しない）。

- データ関連機能 (`kabusys.data`)
  - カレンダー管理（`kabusys.data.calendar_management`）
    - market_calendar テーブルを用いた営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない日については曜日ベース（土日を休日とする）でフォールバックする一貫したロジック。
    - JPX カレンダーを J-Quants から差分取得し market_calendar を更新する夜間バッチジョブ `calendar_update_job` を実装。バックフィル・健全性チェックあり。
  - ETL パイプライン（`kabusys.data.pipeline.ETLResult`, `kabusys.data.etl` 再エクスポート）
    - ETL 実行結果を表す dataclass `ETLResult` を実装（取得・保存件数、品質問題、エラー一覧など）。
    - 差分更新、backfill の方針やテーブル存在チェックなどのユーティリティを提供。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算（`kabusys.research.factor_research`）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
    - Value: PER、ROE（raw_financials から最新財務データを取得）
    - DuckDB 上で SQL を用いて実装し、データ不足時は None を返す設計
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（`calc_forward_returns`）：複数ホライズンをまとめて取得。引数バリデーションあり。
    - IC（Information Coefficient）計算（`calc_ic`）：スピアマン順位相関（ランクに変換して計算）。有効レコードが少ない場合は None を返す。
    - ランク変換ユーティリティ（`rank`）と統計サマリー（`factor_summary`）を実装。
  - `kabusys.research.__init__` で主要関数を再エクスポート（zscore_normalize は data.stats から）。

### 変更 (Changed)
- （初回リリースのため履歴変更はなし）

### 修正 (Fixed)
- （初回リリースのため既知のバグ修正履歴はなし）

### 注意点 / 既知の制約 (Notes)
- OpenAI API 依存:
  - デフォルトモデルは gpt-4o-mini。API キーは引数または環境変数 `OPENAI_API_KEY` を使用。
  - JSON Mode を利用する設計だが、外部の挙動によっては前後に余計なテキストが混入する可能性があるため、パース復元処理を搭載している。
- DB（DuckDB）依存:
  - 一部処理（executemany の空リストなど）で DuckDB のバージョン固有の挙動に対するワークアラウンドを実装。
- 未実装 / 将来対応予定:
  - バリューファクターの一部（PBR・配当利回り）は未実装。
- テストフレンドリー設計:
  - OpenAI 呼び出し部分は内部関数をパッチすることでユニットテストで差し替え可能。
- セキュリティ/運用:
  - `.env` 自動ロードを無効にする `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。OS 環境変数は保護され自動上書きされない設計。

### セキュリティ (Security)
- （初回リリース時点で公開されたセキュリティ修正はなし）

---

今後はバージョンごとに「Added / Changed / Fixed / Deprecated / Removed / Security」セクションを更新していきます。必要に応じて、各関数やモジュールの内部定数（リトライ回数や重み付け等）の変更、AI モデルの切替、DB スキーマ変更などを明記してください。