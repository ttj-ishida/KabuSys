CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に従い、セマンティックバージョニングを採用します。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-01
--------------------

Added
- 初期リリース: パッケージ kabusys を導入。バージョンは 0.1.0。
  - エントリポイント: src/kabusys/__init__.py によるパッケージ公開（data, strategy, execution, monitoring）。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装（デフォルトで自動ロード、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート検出（.git または pyproject.toml を起点に探索）により CWD に依存しないロードを実現。
  - 強力な .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応）。
  - override / protected（OS 環境変数保護）を考慮した .env の読み込み順序: OS 環境変数 > .env.local > .env。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 /環境モード /ログレベル等の取得プロパティを実装。未設定の必須キーは ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値は ValueError）。
- データ基盤（src/kabusys/data）
  - calendar_management:
    - market_calendar テーブルを参照する営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の際は曜日ベースのフォールバック（週末を非営業日扱い）。
    - JPX カレンダー差分取得の夜間バッチ calendar_update_job を実装（J-Quants クライアント呼び出し・バックフィル・健全性チェック・冪等保存）。
    - 最大探索日数やバックフィル日数等の保護ロジックを導入し無限ループや過剰フェッチを回避。
  - pipeline / etl:
    - ETLResult データクラスの導入（取得/保存件数、品質チェック結果、エラー情報の集約）。
    - ETL フロー方針（差分更新・backfill・品質チェックの集約・id_token 注入によるテスト性向上）を実装するための基盤。
    - DuckDB と併用するためのテーブル存在チェック等ユーティリティを追加。
  - etl モジュールは pipeline.ETLResult を公開。
- AI モジュール（src/kabusys/ai）
  - news_nlp:
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価する score_news を実装。
    - ニュース収集ウィンドウ計算（calc_news_window）。JST の前日 15:00 〜 当日 08:30（内部は UTC naive datetime）。
    - バッチ化 (_BATCH_SIZE)、1 銘柄当たりの最大記事数 / 文字数トリム、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - API 呼び出しは再試行（429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフ）。失敗時は該当チャンクをスキップし全体処理を継続するフェイルセーフ設計。
    - レスポンスパースにおける回復処理（前後余計なテキストが混ざる場合に最外の {} を抽出）および未取得銘柄を保護するための部分的 DELETE→INSERT 書き込み戦略（DuckDB executemany の挙動に配慮）。
    - テストしやすさのため OpenAI 呼び出しは _call_openai_api を抽象化しモック差替え可能に。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュース LLM センチメントを組み合わせて日次 market_regime を判定する score_regime を実装。
    - マクロニュースは raw_news からマクロキーワードでフィルタ（最大 _MAX_MACRO_ARTICLES 件）して LLM に送信。
    - OpenAI 呼び出しはリトライ・バックオフ・5xx の判定や JSON パース例外時のフォールバック（macro_sentiment=0.0）などを実装。
    - レジームスコアの合成とラベル化（'bull'/'neutral'/'bear'）を行い、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - ルックアヘッドバイアス防止の設計（datetime.today() 不使用。DB クエリは target_date 未満を明示）。
- Research モジュール（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離率を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括 SQL で算出。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクを返すランク付けユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary: 各ファクター列に対する count/mean/std/min/max/median を計算。
  - data.stats の zscore_normalize を再エクスポート（research パッケージ経由で利用可能）。
- ロギング、エラーハンドリング、設計方針
  - 各モジュールで詳細なログ出力（INFO/DEBUG/WARNING）が行われ、例外時には rollback 処理や安全なフォールバックを行う。
  - ルックアヘッドバイアス防止（datetime.today()/date.today() を直接参照しない）という設計指針が AI モジュール・Research モジュールで徹底されている。
  - DuckDB バージョン差分への互換性配慮（executemany の空リスト制約等）を組み込んでいる。

Fixed
- 初期リリースのため該当なし。モジュール内でのフェイルセーフ動作・例外ログを明文化。

Security
- OpenAI / J-Quants / kabu ステーション / Slack に関する機密情報は環境変数で管理（必須キー: OPENAI_API_KEY（関数引数で代替可）、JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は明示的に ValueError を投げて早期検出する実装。

Notes
- テスト性のため、外部 API 呼び出しを内包する関数（OpenAI 呼び出し等）をモック差し替え可能にしている（ユニットテストでの分離が容易）。
- DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT 想定の保存関数など）。
- 外部依存: DuckDB、OpenAI（openai SDK）の利用を前提としている。

----

注記: この CHANGELOG は提供されたソースコード内容からの推測に基づき作成しています。将来の実装差分やリリースノートは実際のコミット/リリース履歴に基づいて更新してください。