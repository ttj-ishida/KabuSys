CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠します。

バージョン 0.1.0 - 2026-03-28
---------------------------

Added
- パッケージ基盤
  - 初期パッケージ公開: kabusys (バージョン 0.1.0)
  - パッケージの __all__ に data, strategy, execution, monitoring を含め公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - 自動読み込みの探索はパッケージファイル位置から親ディレクトリへ辿り .git または pyproject.toml を基準にプロジェクトルートを特定（CWD 非依存）。
  - .env / .env.local の読み込み優先度: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export 形式、引用符（シングル／ダブル）とバックスラッシュエスケープ、インラインコメントに対応。
  - Settings クラスを導入して、J-Quants / kabu ステーション / Slack / DBパス / 環境種別 (development/paper_trading/live) / ログレベル等のプロパティを提供。必須変数未設定時は ValueError を発生。

- データプラットフォーム (kabusys.data)
  - calendar_management: JPX 市場カレンダーの管理ユーティリティ。
    - 営業日判定・前後営業日取得・期間内営業日一覧取得・SQ日判定等の API 実装。
    - market_calendar が不完全な場合は曜日ベースのフォールバックを行い、一貫性を保つ設計。
    - 夜間バッチ: calendar_update_job による J-Quants API からの差分取得と冪等保存（ON CONFLICT 相当）を実装。バックフィル・健全性チェックあり。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETL パイプライン骨格: 差分取得、保存（idempotent）、品質チェックを想定したインターフェースとユーティリティを実装。
    - DuckDB との相互作用ユーティリティ（最大日付取得等）を実装。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - Momentum: mom_1m, mom_3m, mom_6m、200日移動平均乖離（ma200_dev）を計算する calc_momentum を実装。
    - Volatility/Liquidity: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算する calc_volatility を実装。
    - Value: PER（EPS が有効な場合）、ROE を取得する calc_value を実装。
    - 設計上、prices_daily / raw_financials のみ参照し外部 API にはアクセスしないよう分離。
  - feature_exploration:
    - calc_forward_returns: 指定基準日から各ホライズン後の将来リターン（複数 horizon に対応）を一括で取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装（3 銘柄未満では None）。
    - rank: 同順位は平均ランクとするランク変換実装（丸めで ties の漏れを低減）。
    - factor_summary: count/mean/std/min/max/median 等の統計サマリーを実装。
  - kabusys.research パブリック API として主要関数を __all__ で公開。

- AI / NLP 機能 (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとの記事テキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを算出。
    - JST ベースのニュースウィンドウ計算 calc_news_window を提供（target_date の前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 時刻で処理）。
    - バッチサイズ、最大記事数・最大文字数の制限を設け、トークン膨張を抑止。
    - JSON Mode（厳密 JSON）での応答を期待しつつ、実際には応答前後の余計なテキストをトリムしてパースする耐性を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライロジックを実装。API 失敗時は該当チャンクをスキップしてフェイルセーフで継続。
    - レスポンス検証を実装（results キー・型チェック・未知コード無視・スコアの数値化・±1.0 でクリップ）。
    - DuckDB の executemany の空リスト制約 を考慮した安全な DELETE→INSERT の置換ロジック（部分失敗時に既存データを保護）。
    - テスト用フック: _call_openai_api を patch 可能にしてモック化を容易化。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily から ma200_ratio を算出し、raw_news からマクロ指向のタイトルを抽出するロジックを実装（マクロキーワードリストあり）。
    - OpenAI 呼び出しは JSON モードでマクロセンチメントを取得。API エラー時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - テスト容易性のため _call_openai_api は独立実装でモジュール間結合を避ける設計。

- その他ユーティリティ
  - 複数モジュールで共通する設計方針を明文化（ルックアヘッドバイアス回避のため date.today()/datetime.today() を直接参照しない等）。
  - DuckDB を主要な分析用 DB として想定し、SQL + Python の混成で処理を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / 実装上の重要事項
- セキュリティ・運用
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給。未設定の場合は ValueError を送出する仕様。
  - .env 読み込みはプロジェクトルート検出に依存するため、配布後でも CWD に依存せずに動作する設計。
  - 環境変数の自動上書きは .env.local が優先されるが、OS 環境変数は保護される（protected set により上書き回避）。
- フェイルセーフ
  - 各種外部 API 呼び出しはリトライやフォールバックを備え、致命的な例外を起こさないよう継続可能性を優先する実装（ただし DB 書き込み失敗時は例外を伝播）。
- テスト
  - OpenAI 呼び出し箇所は _call_openai_api を patch して置き換えられるよう設計されており、単体テストでモック化が容易。
- DuckDB 互換性
  - DuckDB の executemany に関する空リスト制約等のワークアラウンドを実装。

今後の予定（未実装／検討中）
- Strategy / execution / monitoring モジュールの具体実装（パッケージ __all__ に含められているが本リリースでは詳細未提供）。
- 追加ファクター（PBR、配当利回り等）やスコアリングロジックの拡張。
- 運用監視・アラート（Slack 通知等）の統合。

ライセンス、貢献方法等はリポジトリの README を参照してください。