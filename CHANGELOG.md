Keep a Changelog
=================

すべての注目に値する変更をこのファイルに記録します。
このプロジェクトはセマンティックバージョニングに従います（http://semver.org/）。

[Unreleased]
------------

追加
- なし（初回リリースに向けた安定化中の変更は本節に記載します）。

変更
- なし。

修正
- なし。

[0.1.0] - 2026-04-03
--------------------

初回リリース — 基本機能の実装

追加
- パッケージ基本情報
  - kabusys パッケージ初期化（__version__ = 0.1.0）。主要サブパッケージ（data, research, ai, monitoring, execution, strategy 等）の公開準備。

- 設定・環境管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装（プロジェクトルート検出: .git or pyproject.toml）。
  - .env/.env.local の読み込み優先度（OS 環境変数 > .env.local > .env）と、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - export 形式やシングル／ダブルクォート、エスケープ、インラインコメントの取り扱いを考慮した .env 行パーサを実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境種別 / ログレベル等のプロパティ（必須チェックやデフォルト値含む）を用意。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出・ai_scores テーブルへ保存する処理を実装。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを提供（calc_news_window）。
    - バッチサイズ制御、1銘柄あたりの記事数および文字数トリム、レスポンスの厳密なバリデーション、スコアのクリップ（±1.0）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフによるリトライ実装。
    - 部分失敗時に既存スコアを消さないための idempotent な DB 書き込み戦略（該当コードのみ DELETE→INSERT）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込みを実装。
    - マクロニュース抽出のキーワードリスト実装、LLM 呼び出しの再試行・フォールバック（API 失敗時は macro_sentiment=0.0）。
    - 設計上、datetime.today() / date.today() を直接参照せずルックアヘッドバイアスを防止。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB 登録優先、未登録日は曜日ベースでフォールバック。
    - calendar_update_job による J-Quants からの差分取得 / バックフィル / 健全性チェック実装（lookahead / backfill / sanity checks）。
  - ETL パイプライン（pipeline）＆インターフェース（etl）
    - ETL の概念実装（差分取得、保存、品質チェックとの統合）を実装。
    - ETLResult データクラスを提供し、取得件数／保存件数／品質問題／エラー等を集約・辞書化できるようにした。
    - テーブル存在チェック・最大日付取得等のユーティリティを実装（DuckDB 前提）。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER, ROE）、Liquidity 指標の計算関数を実装。DuckDB 内の prices_daily / raw_financials を参照。
    - データ不足時の None 扱い、営業日ベースの窓・スキャン幅の考慮、ログ出力あり。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を避け、標準ライブラリと DuckDB クエリで完結。

共通設計上の配慮（全体）
- ルックアヘッドバイアス防止: 日付を外部引数で受け取り内部で date.today() を参照しない方針を多くのモジュールで採用。
- DB 書き込みは冪等化（DELETE→INSERT / ON CONFLICT またはトランザクション）を意識。
- OpenAI 呼び出し周りは堅牢なエラーハンドリングとリトライ、レスポンスパースのフォールバックを実装。
- DuckDB を前提としたクエリ効率・互換性（executemany の空リスト回避等）を考慮。

変更
- 初期実装のため該当なし。

修正
- 初期実装のため該当なし。

破壊的変更
- なし。

既知の制限 / 注意点
- OpenAI API キー未設定時は ValueError を送出する設計（呼び出し側で管理必須）。
- DuckDB のバージョン差異（配列バインドや executemany の挙動）に注意する実装箇所あり。
- 一部機能は J-Quants クライアント（jquants_client）等外部モジュールに依存するため、実行環境での設定・認証が必要。

署名
- 初回リリース（0.1.0）は上記モジュール群の初期実装を含みます。今後のリリースではテスト、ドキュメント、補完的なユーティリティ、バグ修正を継続予定です。