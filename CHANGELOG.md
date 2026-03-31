# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  

最新リリース: 0.1.0 (初回公開)

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開インターフェース: data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能を実装。
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードの無効化が可能。
  - .env パーサーの実装（コメント、export プレフィックス、クォート内のエスケープ等を考慮）。
  - 上書き制御（override）と OS 環境変数保護（protected）に対応。
  - Settings クラスを導入し、各種必須設定（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）や
    DB パス（DUCKDB_PATH / SQLITE_PATH）、環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）をプロパティで安全に取得。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（pipeline）と ETLResult データクラスを実装し、ETL の実行結果・品質情報を構造化して返却可能に。
  - jquants クライアント経由での差分取得→保存の想定（実際の jquants_client 実装は依存）。
  - calendar_management モジュールを実装：
    - JPX マーケットカレンダー用テーブル操作と夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DBにカレンダーがない/未登録日の場合は曜日ベースでフォールバックする堅牢な設計。
    - 最大探索範囲・バックフィル・健全性チェック等の安全策を導入。

- 研究（research）
  - ファクター計算（research.factor_research）:
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（price / EPS）、ROE（raw_financials からの取得）。（PBR・配当利回りは未実装）
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials を参照。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（例: 1,5,21 営業日）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクで処理。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージの公開 API を整理（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- AI / ニュース処理（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode でバッチスコアリングを実行して ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数・文字数制限（デフォルト: 10 件 / 3000 文字）でトークン肥大化を抑制。
    - リトライと指数バックオフ（429 / ネットワーク断 / タイムアウト / 5xx を対象）。
    - レスポンス検証ロジック（JSON パース、results 配列、code/score の検証、スコアクリッピング）。
    - 部分成功時の DB 書き換え戦略（対象コードのみ DELETE → INSERT）により既存スコアの保護を実現。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に実装（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（日経225連動型）200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照してスコアを算出、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しフェイルセーフ: 失敗時は macro_sentiment = 0.0 にフォールバック。
    - OpenAI クライアントを生成して gpt-4o-mini を使用。リトライ戦略を実装。

- 実装方針・品質面の注力点
  - ルックアヘッドバイアス防止: いずれの処理も datetime.today() / date.today() を内部で参照せず、必ず引数 target_date を基準に処理。
  - DuckDB をデータレイヤーとして採用。SQL と Python を組み合わせて高効率に集計・窓関数を利用。
  - DB 書き込みは可能な限り冪等になるよう設計（DELETE → INSERT、ON CONFLICT 戦略想定）。
  - OpenAI 等外部 API の呼び出しはリトライ / バックオフ / フェイルセーフを実装して堅牢化。
  - ロギングを各処理に埋め込み、失敗時の挙動を明確化。

### Fixed
- 初期実装として、API レスポンスのパースエラーや接続エラーが発生した場合に例外を上位へ投げず、ロギングしてフェイルセーフ値で継続する挙動を確立（news_nlp, regime_detector）。

### Known limitations / Notes
- OpenAI API の利用には OPENAI_API_KEY の設定が必須（関数引数でキー注入も可能）。
- jquants_client や Slack 連携など外部クライアントの具体実装は別モジュール/外部依存を想定。
- 一部指標（PBR・配当利回り等）は現時点で未実装。
- DuckDB のバージョンによっては executemany の空リストバインド等に制約があるため、それらを回避する実装になっている。
- 本リリースは初版であり、将来的に API 仕様や返却スキーマの変更により互換性破壊の可能性あり（次バージョンで明示）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの詳細実装および統合テスト
- CI での DuckDB を用いた統合テスト、OpenAI 呼び出しのモック確立
- 追加ファクター（PBR・配当利回り）やリスク管理ロジックの導入

（必要であれば、各モジュールごとの更に細かい変更点やサンプル使用例を別ドキュメントとして追記できます。）