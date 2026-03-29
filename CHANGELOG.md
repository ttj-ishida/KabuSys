# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

現在のバージョン: 0.1.0

## [Unreleased]
- 開発中の変更点をここに記載します。

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージ公開: data, research, ai, monitoring, strategy, execution（__all__ にてエクスポート）。

- 設定 / 環境管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を自動ロードする仕組みを実装。
    - ロード順: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検出。
  - .env パーサを実装:
    - コメント行 / export 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理。
  - Settings クラスを提供（settings オブジェクトをエクスポート）:
    - 必須環境変数チェック (_require)：JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を要求。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを設定。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（有効値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存する処理を実装。
    - 特徴:
      - JST ベースのタイムウィンドウ計算（前日15:00〜当日08:30、内部は UTC naive）。
      - 1銘柄あたり最大記事数・文字数でトリム（トークン肥大化対策）。
      - 最大チャンクサイズ（_BATCH_SIZE=20）でバッチ送信。
      - JSON Mode を期待し、応答をバリデートしてスコアを ±1.0 にクリップ。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
      - 部分失敗を考慮した冪等的な DB 書き込み（対象コードのみ DELETE → INSERT）。
      - テスト容易性のため _call_openai_api をパッチ可能に実装。
  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに保存。
    - 特徴:
      - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス回避）。
      - マクロニュースは news_nlp.calc_news_window と連携してウィンドウ内のタイトルを抽出、LLM で macro_sentiment を取得。
      - OpenAI 呼び出しに対して再試行ロジックとフォールバック（失敗時 macro_sentiment=0.0）。
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試行。
      - _call_openai_api は news_nlp と独立した別実装でモジュール結合を防止。

- データ処理（kabusys.data）
  - ETL パイプライン（data.pipeline）
    - ETLResult データクラスを実装・公開（data.etl で再エクスポート）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）に対応する設計。
    - DuckDB を利用した最終日付取得ユーティリティ、テーブル存在チェックなどを実装。
    - ETL の結果表現（品質問題とエラー集計）を to_dict() で整形。
  - マーケットカレンダー管理（data.calendar_management）
    - market_calendar テーブルを使った営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日ベースのフォールバック（平日を営業日とみなす）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新する夜間バッチ実装（バックフィル・健全性チェックあり）。
    - 最大探索日数制限、将来日付の健全性検査、バックフィル日数などの保護ロジックを実装。
  - jquants_client との連携を想定（データ取得・保存は jquants_client を利用する設計）。

- Research（kabusys.research）
  - ファクター計算（research.factor_research）
    - calc_momentum: 1M / 3M / 6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials に基づき PER / ROE を計算（最新報告日ベース）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースで安定して算出。
  - 特徴量探索（research.feature_exploration）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとする安定したランク化実装（round による丸めで float の ties を扱う）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

### 改善 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- 各モジュールでのフォールバック・例外処理を強化:
  - AI モジュールは OpenAI API の失敗時に例外を上位へ直接伝播させずフォールバック（スコア 0.0 またはスキップ）することで全体処理の継続性を確保。
  - DB 書き込みでの失敗時に ROLLBACK を試行し、ROLLBACK 自体の失敗をログ出力して上位へ伝播。

### 注意 / マイグレーション (Notes)
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する関数（score_news, score_regime）を呼ぶには OPENAI_API_KEY が必要（引数での注入も可能）。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
- 自動 .env ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- テスト容易性:
  - OpenAI 呼び出し（_call_openai_api）はユニットテストで patch 可能に設計。API 呼び出しをモックして動作検証が可能。
- セーフガード:
  - ルックアヘッドバイアス回避のため、日時取得や DB クエリにおいて target_date より未来のデータを参照しない設計。

### 既知の制限 (Known limitations)
- 現時点で PBR・配当利回り等の一部バリューファクターは未実装（calc_value は PER / ROE のみ）。
- DuckDB バージョン依存の挙動（executemany の空リスト制約など）に合わせた実装上の回避が含まれる。
- OpenAI の応答整形は JSON Mode を想定しているが、稀に混入する前後テキストについては簡易抽出で復元を試みるのみ。

---

貢献・バグ報告・改善案は issue / pull request を通じて歓迎します。