CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。
このプロジェクトの初期リリースを記録しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-02
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイルまたは OS 環境変数から設定を自動的に読み込む機能を追加。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
    - .env パーサを実装:
      - コメントや先頭の "export " プレフィックス対応。
      - シングル/ダブルクォートの内部エスケープ処理、インラインコメントの扱いなど堅牢なパースを実装。
    - .env 読み込み時の上書き制御:
      - override, protected の概念を導入し OS 環境変数を保護。
    - Settings クラスでアプリ設定をプロパティとして公開:
      - J-Quants / kabu API / Slack / DB パス / 監視閾値 / システム設定など多数のプロパティを提供。
      - 必須設定は _require() により未設定時に ValueError を発生させる。
      - KABUSYS_ENV (development, paper_trading, live) と LOG_LEVEL の検証を実装。
      - Path 型プロパティは expanduser を行う。

- AI（ニュース & レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事群から銘柄ごとのセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores テーブルへ書き込む機能を追加。
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ計算（UTC 変換）を実装（calc_news_window）。
    - 1銘柄当たり最大記事数 / 最大文字数でトリムすることでトークン肥大化に対処（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 銘柄を最大 20 件ずつバッチ処理（_BATCH_SIZE）。
    - API 呼び出しは JSON Mode を利用し、レスポンスのバリデーションとスコアクリッピング（±1.0）を実施。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - 部分成功時に既存スコアを保護するため、書き込みは対象コードのみ DELETE → INSERT を実行（DuckDB executemany の空リスト回避を考慮）。
    - テスト容易性のため _call_openai_api を patch できる設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - ma200_ratio 計算は target_date 未満のデータのみを利用しルックアヘッドを防止。
    - LLM の評価は最大 20 件のマクロ記事タイトルを取り込み、JSON レスポンスをパースして macro_sentiment を取得。
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアはクリップし閾値によりラベル付与。結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK ハンドリング）。
    - OpenAI API キーは引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照。

- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理: market_calendar テーブルを用いた営業日判定ロジックを追加。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar がない（未取得）場合は土日ベースのフォールバックを使用。
      - 最大全探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ回避。
    - calendar_update_job を実装:
      - J-Quants API（jquants_client）から差分取得し、バックフィル日数を含めて冪等更新（ON CONFLICT / 上書き）を行う。
      - 健全性チェック（将来日付の異常検出）や API エラー時の安全な振る舞いを実装。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基本インターフェースを実装。
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題リスト・エラー一覧などを保持）。
    - 差分取得、バックフィル、品質チェックの設計方針を実装（jquants_client / quality モジュールと連携）。
    - ETLResult.to_dict() で品質問題をシリアライズ可能にして監査ログ用途に配慮。
    - パイプライン内の DB 存在チェックや最大日付取得ユーティリティを実装。

- Research（因子・特徴量）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）、ma200 乖離、ATR/相対ATR、平均売買代金、出来高比率、財務指標（PER/ROE）など主要ファクターを DuckDB SQL ベースで計算する関数を追加（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None 扱い、営業日ベースのウィンドウ設計などを実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証付き）、IC（スピアマンランク相関）calc_ic、rank（同順位は平均ランク）および factor_summary（基本統計）を追加。
    - pandas 等外部依存なしで標準ライブラリ + DuckDB SQL による実装。
  - src/kabusys/research/__init__.py
    - 主要関数をパブリック API として再エクスポート。

- その他
  - src/kabusys/ai/__init__.py と src/kabusys/research/__init__.py で API を限定公開。
  - ロギングを各モジュールに導入し、失敗時の警告・情報を出力するようにした。
  - テストしやすさを考慮し、API 呼び出し関数（_call_openai_api 等）は patch 可能な設計に。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- 環境変数ハンドリングで OS 環境変数を protected として上書きを防止する仕組みを導入。
- OpenAI API キー・Slack トークン等は Settings 経由で必須チェックを行い、未設定時は明確なエラーメッセージを返す。

Notes / Implementation details / Safeguards
- ルックアヘッドバイアス防止:
  - AI モジュールや Research モジュールは内部で datetime.today()/date.today() を直接参照せず、必ず target_date を明示的に受け取る設計。
  - prices_daily などのクエリは target_date 未満（排他）／target_date を明示的に扱うことで未来データ参照を防止。
- フェイルセーフ:
  - LLM/API の失敗やパース失敗時には例外を投げずフォールバック（例: macro_sentiment=0.0、該当チャンクのスキップ）で継続する設計。
- DB 書き込み:
  - market_regime / ai_scores などは冪等な置換処理（DELETE → INSERT）を採用、トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を維持。
- DuckDB の仕様（executemany の空リスト不可）に合わせたガードを実装。

Known limitations
- （本リリースは初期実装のため、今後のテストで追加の堅牢化・最適化を予定）
- OpenAI 利用に伴うコスト・レイテンシや API バージョン変化への対応は今後要監視。
- jquants_client / quality モジュールの具体的実装は外部依存（本コードはそれらを呼び出す設計）。

作者
- kabusys 開発チーム

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース手順に基づき調整してください。）