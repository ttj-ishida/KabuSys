CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-01
--------------------

初回公開リリース。以下のモジュールと機能を実装しました。

Added
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = 0.1.0、公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に一部列挙）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）を自動でプロジェクトルートから読み込む自動ロード機能を実装。
    - ルート判定は .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは以下をサポート・考慮:
    - 空行・コメント行、export KEY=val 形式、シングル/ダブルクォート（エスケープ処理）、インラインコメントの扱い。
  - 実行時に利用できる Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境 などのプロパティを環境変数から取得。
    - 必須キー未設定時は ValueError を送出する _require() を利用。
    - KABUSYS_ENV の妥当性（development / paper_trading / live）チェック、LOG_LEVEL の妥当性チェック。
    - デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合・トリムして OpenAI（gpt-4o-mini、JSON Mode）へ送信。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたり記事上限/文字数上限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - エラー／429／ネットワーク断／タイムアウト／5xx に対して指数バックオフでリトライ。非リトライ例外は対象チャンクをスキップ。
    - レスポンスは厳密な JSON を期待しつつ、前後に余分なテキストが混ざるケースからの復元ロジックを実装。
    - スコアは ±1.0 にクリップし、成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時の保護を実現。
    - ニュース収集ウィンドウ定義（JST基準）と calc_news_window ユーティリティを提供（前日15:00〜当日08:30 JST）。
    - テスト容易性のため OpenAI 呼び出し箇所はモジュール内で差し替え可能（_call_openai_api を patch 可能）。
    - 空記事や API 未応答時のフェイルセーフ（スコア取得銘柄数 0 を返す）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（bull/neutral/bear）。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロニュース抽出はキーワードリストを用いて raw_news からタイトルを最大 _MAX_MACRO_ARTICLES=20 件取得。
    - OpenAI 呼び出しは gpt-4o-mini を使用、JSON Mode で {"macro_sentiment": float} を期待。API の失敗時は macro_sentiment=0.0 にフォールバック。
    - 合成スコアは clip(-1.0, 1.0) し閾値によりラベル付与。結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未指定時は ValueError。

- Data モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日フォールバックで一貫した挙動を提供。
    - calendar_update_job を実装し J-Quants API（jquants_client）と連携して差分取得・バックフィル・保存を行う。健全性チェックやバックフィル日数を実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを実装し公開（kabusys.data.etl で再エクスポート）。
    - 差分更新・バックフィル・品 質チェック（quality モジュール）・idempotent 保存の設計を反映する下地を提供。
    - DuckDB の存在チェックや最大日付取得ユーティリティを実装。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン, ma200_dev）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）等のファクター計算関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB を用いた SQL ベースの計算（prices_daily, raw_financials のみ参照）。データ不足時の None 考慮。
  - feature_exploration
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman の ρ をランクベースで算出）
    - 統計サマリー: factor_summary(records, columns)
    - ランク変換ユーティリティ: rank(values)
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - 研究用ユーティリティ公開
    - kabusys.research パッケージで主要関数をまとめてエクスポート（zscore_normalize は kabusys.data.stats からの再利用を前提）。

Design / Implementation notes
- ルックアヘッドバイアス対策
  - 各 AI/研究処理で datetime.today() や date.today() を直接参照せず、呼び出し側から target_date を渡す設計。
  - DB クエリでは target_date 未満や LEAD/LAG の適切な使用で将来データ参照を防止。
- OpenAI 連携
  - gpt-4o-mini を JSON Mode（response_format={"type": "json_object"}）で利用。
  - ネットワーク/429/5xx は再試行の対象、その他はスキップ（フェイルセーフ）。
  - テストのために _call_openai_api をモック可能にしている。
- DuckDB 関連の互換性対策
  - executemany に空リストを渡せない DuckDB（例: 0.10）の挙動を考慮して、空チェックを行う実装。
  - トランザクションの BEGIN / COMMIT / ROLLBACK により冪等・安全性を確保。ROLLBACK 失敗時に警告ログを出す。
- ロギングとしきい値
  - 各処理で詳細な INFO/DEBUG/WARNING ログを出力するように設計（例: score_news のチャンク数・スコア取得数、score_regime の ma200_ratio 等）。
  - 監視用の閾値プロパティ（CPU/MEM/DISK %）を Settings から取得可能。

Notes (重要な運用上の注意)
- 必須環境変数
  - OPENAI_API_KEY（AI API 呼び出し）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション連携）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用）
  - 上記が未設定のまま関連関数を呼ぶと ValueError が発生します。
- デフォルト DB パス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- テスト容易性
  - OpenAI 呼び出しを差し替えられる設計と、.env 自動読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）によりユニットテストが容易。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Deprecated
- なし。

Breaking Changes
- 初回リリースにつき該当なし。

参考（使い方の簡単な例）
- 環境変数を用意して、.env をプロジェクトルートに配置。
- DuckDB 接続を渡して関数を呼び出す例:
  - from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=None)  # api_key を None にすると OPENAI_API_KEY を参照
  - from kabusys.research.factor_research import calc_momentum
    calc_momentum(conn, target_date)

以上。今後のリリースでは監視・実行・ストラテジーの実装拡張、テストカバレッジ強化、運用ドキュメントの追加を予定しています。