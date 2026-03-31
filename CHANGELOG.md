# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31

### 追加
- パッケージ初期公開: kabusys v0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py にてバージョンと公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 設定/環境変数管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env を探索（CWD に依存しない）。
    - export プレフィックス、クォート文字列、インラインコメント、エスケープシーケンス等に対応する堅牢な .env パーサを実装。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須キー検査用ヘルパ (_require) と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL）やパスの展開（duckdb/sqlite パス）を実装。
- AI 関連
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を集約して OpenAI (gpt-4o-mini) に送信し、銘柄ごとのセンチメント ai_score を計算して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）、記事トリム（記事数・文字数制限）、バッチ処理（最大 20 銘柄/チャンク）。
    - OpenAI 呼び出し時のリトライ（429、ネットワーク断、タイムアウト、5xx を対象）と指数バックオフを実装。
    - レスポンスのバリデーションを実装（JSON 抽出、results 配列検証、コード照合、数値検証、スコアの ±1.0 クリップ）。
    - 部分成功を考慮した冪等的 DB 書き換え（対象コードのみ DELETE → INSERT）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算し market_regime テーブルへ書き込む。
    - prices_daily からのデータ取得は target_date 未満の排他条件によりルックアヘッドバイアスを防止。
    - マクロ記事抽出（マクロキーワードリスト）→ OpenAI でマクロセンチメント評価 → 合成スコア化。
    - OpenAI 呼び出しのリトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
- データ基盤 / ETL
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラスを公開（ETL のフェッチ数・保存数・品質問題・エラー情報を保持）。
    - 差分更新、バックフィル、品質チェックの方針を実装指針としてコードに反映。
    - DuckDB 上のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 未取得時の曜日ベースフォールバック、DB 値優先の一貫性、探索上限（_MAX_SEARCH_DAYS）やバックフィルの方針を実装。
    - calendar_update_job: J-Quants API からの差分取得 → 保存（ON CONFLICT DO UPDATE）を実行する夜間バッチ処理を実装（バックフィルと健全性チェックあり）。
- リサーチ（ファクター計算・特徴量解析）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER・ROE）等の定量ファクターを DuckDB + SQL で計算する関数を提供（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None 返却や、営業日スキャン範囲のバッファ設計を実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部依存なしで標準ライブラリと DuckDB のみで実装。
  - src/kabusys/research/__init__.py により主要関数を再エクスポート。
- データクライアント補助
  - src/kabusys/data/__init__.py と jquants_client からの利用を想定（ETL とカレンダー更新で使用）。
- ロギングと警告
  - 各モジュールで詳細な logger 呼び出しを追加（INFO/DEBUG/WARNING/EXCEPTION）し、障害時にフェイルセーフで継続する挙動を多くの箇所で採用。

### 変更
- 初回公開のため該当なし。

### 修正
- 初回公開のため該当なし。

### 破壊的変更
- 初回公開のため該当なし。

### セキュリティ
- 初回公開のため該当なし。

### 注記 / 重要な動作上のポイント
- OpenAI API
  - news_nlp / regime_detector は OpenAI (gpt-4o-mini) を利用する。API キーは引数で注入可能（api_key）か、環境変数 OPENAI_API_KEY を参照する。未設定の場合は ValueError を送出する。
  - API 呼び出しでの一時エラーはリトライされるが、最終的に失敗した場合はスコア計算を 0.0 やスキップでフォールバックして処理継続する設計。
- .env 自動ロード
  - プロジェクトルートを検出できなければ自動ロードはスキップされる。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 互換性
  - 一部の executemany やリスト型バインドは DuckDB バージョン差異を考慮して実装（空リストの executemany 回避など）。
- ルックアヘッドバイアス対策
  - 日付参照は date.today() / datetime.today() を直接用いない方針が多くの処理（AI スコア・レジーム判定・ニュースウィンドウ等）に反映されています。target_date を明示して呼び出してください。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの具体的実装の追加。
- テストカバレッジ強化と外部 API 呼び出しのモックを含むユニットテスト追加。
- エラーメトリクスや監視（Sentry 等）統合。

--- 

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて調整してください。）