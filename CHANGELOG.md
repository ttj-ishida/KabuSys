CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: コードベースから推測して作成しています。各項目は実装内容・設計方針・ログメッセージ等から導出した要約です。

[Unreleased]
-------------

- ドキュメント／メタ
  - パッケージ初期開発段階の補足メモや将来の改善点を収集中。

- 注意事項（重要）
  - OpenAI を利用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY または関数引数で API キーを受け取ります。未設定時は ValueError を送出します。
  - .env 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - 環境変数必須項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト DB パス:
    - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可能）
    - SQLite: data/monitoring.db（環境変数 SQLITE_PATH で変更可能）

- 既知の仕様・想定挙動
  - OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（厳密な JSON 出力）でレスポンスを受け取る設計。
  - LLM 呼び出しに対してはリトライ（指数バックオフ）や 5xx/ネットワーク・429 の判別などの堅牢化処理が組み込まれており、API 失敗時はフェイルセーフ（例えば macro_sentiment=0.0 や該当チャンクのスキップ）で継続します。
  - DB 書き込みは冪等性を重視（DELETE → INSERT のパターンや ON CONFLICT 方針を想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護しています。

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期版を追加。
  - __version__ = "0.1.0" を設定し、主要サブパッケージ（data, research, ai, monitoring, strategy, execution 相当を想定）を __all__ で公開。

- 設定管理
  - 環境変数・.env 管理モジュールを実装（kabusys.config）。
    - .env / .env.local の自動読み込み（OS 環境変数を保護する protected ロジック、.env.local は上書き）を提供。
    - 行解析は export 形式やクォート内エスケープ、インラインコメント対応を含む堅牢なパーサを実装。
    - 必須環境変数チェック（_require）や env/log_level の値検証（許容値チェック）を実装。
    - 各種設定プロパティ（J-Quants, kabu API, Slack, DB パス, 環境モード判定等）を提供。

- AI（自然言語処理）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを統合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄 / チャンク）、トークン過大対策（記事数上限／文字数上限）、JSON レスポンス検証、スコアクリップ、部分失敗時の DB 保護（対象コードのみ DELETE→INSERT）などを実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対するリトライとログ出力を実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を判定し market_regime テーブルへ保存。
    - prices_daily からのデータ取得はルックアヘッド防止（target_date 未満のみ使用）。LLM 呼び出しの失敗は macro_sentiment=0.0 で継続。
    - OpenAI 呼び出しは独立した内部実装でモジュール結合を避ける設計。

- データ基盤（data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得／バックフィル／品質チェックのための ETLResult データクラスを追加。
    - DuckDB に対する最終日付取得やテーブル存在チェック等のユーティリティを実装。
    - 市場カレンダー管理（kabusys.data.calendar_management）
      - market_calendar を用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
      - DB 未取得時は曜日ベースのフォールバック（週末除外）を使用。
      - calendar_update_job により J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）を実装。

- リサーチ（research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR・ATR 比率・出来高関連）、Value（PER/ROE）等の計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、データ不足時の None 処理やログ出力を実装。

  - 特徴量解析ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン）、IC（スピアマンランク相関）計算、ランク付けユーティリティ、統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せずに標準ライブラリと DuckDB を使用。

Changed
- （初版リリースのため該当なし）

Fixed
- （初版リリースのため該当なし）

Security
- 環境変数や API キーは明示的に必須扱いとし、未設定時は ValueError を送出して不正な運用を防止。
- .env 読み込み時に OS 環境変数を上書きしない保護機構を実装（protected set）。

Notes / Implementation details
- ルックアヘッドバイアス対策
  - AI・研究処理（ニュースウィンドウや価格クエリ）は datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す設計。DB クエリは target_date 未満/前日ベース等の排他条件を用いることで将来情報の混入を防止しています。

- トランザクションと冪等性
  - AI スコア書き込みやレジーム書き込み等は BEGIN/DELETE/INSERT/COMMIT のパターンで冪等性を保証し、エラー時は ROLLBACK を試みる設計です。ROLLBACK に失敗した場合は警告ログを出力します。

- OpenAI レスポンスの堅牢な解析
  - JSON パースに失敗した場合でも本文中の最外の {} を抽出して復元を試みるなど、実運用での不整合に備えた実装が含まれます。

- DuckDB 互換性
  - executemany に空リストを渡せない挙動（DuckDB 0.10 の既知制約）を考慮し、空のときは実行をスキップするガードを実装しています。

Breaking Changes
- なし（初回公開）

(以上)