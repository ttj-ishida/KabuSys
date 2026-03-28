# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、本CHANGELOGはリポジトリ内のコード（src/kabusys 以下）を元に推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加
- パッケージ基盤
  - パッケージルート: kabusys（version = 0.1.0）。
  - パッケージ公開 API: __all__ = ["data", "strategy", "execution", "monitoring"] を定義。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込むユーティリティを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準にパッケージ内からルートを探索（CWD に依存しない挙動）。
  - .env のパースは export KEY=val, シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 自動ロード優先度: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスを提供し、環境変数経由での設定取得をプロパティとして簡易化:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV 値検証（development, paper_trading, live）
    - LOG_LEVEL 値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev ラッパー

- AI（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチで送信して銘柄毎のセンチメント（ai_score）を算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ制御: 最大 20 銘柄/コール、各銘柄は最新 N 件かつ最大文字数でトリム（デフォルト: 10 件・3000 文字）。
    - リトライ/バックオフ: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON の results 配列、code と数値 score を検証。未知コードは無視。スコアは ±1.0 にクリップ。
    - DB 書き込み: 成功したコードのみ置換（DELETE → INSERT）して部分失敗時の既存データ保護。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - テスト性: OpenAI 呼び出し _call_openai_api は patch 可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定。
    - MA の計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを防止。データ不足時は中立（ma200_ratio=1.0）を採用。
    - マクロニュースは raw_news からマクロキーワードでフィルタ（最大 20 記事）。記事が無ければ LLM 呼び出しを行わずマクロスコア=0.0。
    - OpenAI 呼び出しは retry/backoff を実装し、最終的に失敗した場合は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データ（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得 → 保存（jquants_client で idempotent 保存）→ 品質チェックを行う ETLResult 型とユーティリティを実装。
    - ETLResult dataclass に品質問題・エラーの集約、has_errors / has_quality_errors / to_dict を提供。
    - 内部ユーティリティ: テーブル存在確認や最大日付取得など。
  - ETL 再エクスポート（kabusys.data.etl）
    - ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日の判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（平日を営業日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等に更新（バックフィル、先読み、健全性チェックを実装）。
    - 最大探索日数やバックフィル日数等の安全パラメータを定義し無限ループや異常データを防止。
  - jquants_client / quality などの外部連携を想定した設計（実装箇所はクライアントモジュールに委譲）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金 / 出来高変化率）を計算する関数を提供:
      - calc_momentum(conn, target_date)
      - calc_value(conn, target_date)
      - calc_volatility(conn, target_date)
    - DuckDB の SQL(Window 関数) を利用して営業日ベースの窓処理を実装。データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)
      - デフォルト horizons=[1,5,21]。horizons の検証あり（1〜252 日）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関を独自実装。有効レコード 3 件未満なら None。
    - ユーティリティ: rank(values), factor_summary(records, columns)
      - rank は同順位の平均ランクを返す実装。factor_summary は count/mean/std/min/max/median を算出。
    - 外部依存を極力排し、標準ライブラリ + duckdb で動作する設計。

### 変更（設計上の注意点）
- 全ての「日付を参照する」処理（score_news / score_regime / 各種計算）は datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）で、target_date を明示的に渡すことを想定。
- OpenAI への呼び出し部分はテスト容易性のため patch 可能に実装（ユニットテストで差し替え可能）。
- DuckDB を主要なストレージ・計算基盤として利用。executemany の空リストバインドに関する注意（DuckDB 0.10 の制約）への配慮あり。

### 修正（バグ修正等）
- （本バージョンは初回のため無し）

### 既知の制約 / 注意点
- OpenAI API（gpt-4o-mini）を利用する機能は OPENAI_API_KEY が必要。未設定時は ValueError を発生させる箇所あり。
- .env 自動読み込みはプロジェクトルートが検出できない場合スキップされる（パッケージ配布後の安全設計）。
- market_calendar がまばらな場合でも next/prev/get_trading_days が一貫した挙動となるようフォールバックロジックを採用しているが、完全なカレンダーデータが望ましい。
- AI モジュールは外部 API 呼び出しに依存するため、ネットワーク障害・レートリミット等が発生した際はフェイルセーフとして該当部分をスキップして継続する実装（部分的な欠損が発生し得る）。

---

（補足）
- 上記はソースコードからの挙動・設計推測に基づく CHANGELOG です。実際の機能要件や外部依存（jquants_client 等）の実装状況により差異がある可能性があります。必要であれば特定モジュールごとにより詳細な変更点（関数シグネチャ、返り値例、エラーメッセージ等）を追記します。