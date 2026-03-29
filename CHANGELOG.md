# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

現在のバージョン: 0.1.0 (初回公開)

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。以下は主な追加機能、設計上の方針、既知の挙動・制約のまとめです。

### 追加
- パッケージ初期化
  - kabusys パッケージを作成。__version__ = "0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
  - 読み込み順序: OS 環境 > .env.local > .env（.env.local は既存 OS 環境を protected として上書き可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 強力な .env パース実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理等に対応）。
  - 必須環境変数取得用 _require() と Settings クラスを提供。主なキー:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - OPENAI_API_KEY（AI モジュールで使用）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス付与）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）

- AI モジュール (kabusys.ai)
  - ニュースセンチメント集計 (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI の gpt-4o-mini でセンチメントを評価。
    - チャンク処理（最大 20 銘柄/API コール）、1 銘柄あたり最大記事数・文字数制限（トークン肥大化対策）。
    - JSON Mode 想定のレスポンス検証と復元処理（前後余計テキストの切り出し等）。
    - 429、接続断、タイムアウト、5xx に対する指数バックオフリトライ。
    - API 失敗時はスキップして継続（フェイルセーフ）。テスト用に _call_openai_api を patch して差し替え可能。
    - ai_scores テーブルへの冪等書き込み（DELETE→INSERT。部分失敗時に既存スコアを保護するため対象コードだけ書換え）。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（bull/neutral/bear）。
    - マクロニュースは raw_news からマクロキーワードでフィルタして LLM に投げる（最大 20 件）。
    - OpenAI 呼び出しに対するリトライ・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 で継続。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - 公開関数: score_regime(conn, target_date, api_key=None)
    - LLM モデル: gpt-4o-mini、JSON 出力を期待。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定/探索ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録値を優先、未登録日は曜日（平日）ベースのフォールバック（カレンダーデータが部分的でも一貫した挙動を保証）。
    - 夜間バッチジョブ calendar_update_job(conn, lookahead_days=90)
      - J-Quants API から差分取得（jquants_client 経由）、ON CONFLICT DO UPDATE 相当で冪等保存。
      - バックフィル（直近数日を再フェッチ）や健全性チェック（過度に将来日がある場合はスキップ）を実装。

  - ETL パイプライン (pipeline)
    - ETLResult データクラスを提供（取得件数、保存件数、品質チェック結果、エラー概要等を格納）。
    - 差分更新・バックフィル・品質チェックを想定した設計。jquants_client と quality モジュールを統合。
    - data.etl は ETLResult を再エクスポート。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/NULL の場合は None）。
    - DuckDB を用いた窓関数ベースの実装で大量データに対応。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマン Rank 相関（IC）を計算。サンプル不足時は None を返す。
    - factor_summary: カラム毎の基本統計量（count, mean, std, min, max, median）を計算。
    - rank ユーティリティ: 同順位は平均ランクで扱う（丸めで ties の漏れを防止）。

### 変更
- （初回リリースにつき該当なし）

### 修正
- （初回リリースにつき該当なし）

### セキュリティ
- （初回リリースにつき該当なし）

### 既知の挙動・注意点
- OpenAI 連携
  - OPENAI_API_KEY を引数で注入可能（api_key パラメータ）。未指定で環境変数がない場合は ValueError を送出。
  - API レスポンスのパース失敗や 5xx 等はフェイルセーフでスコア 0.0 やスキップを採用して、パイプライン全体の停止を防ぐ設計です。
  - テスト容易性のため、各モジュールにある内部 _call_openai_api を unittest.mock.patch で差し替えられる。

- データ不足時のフォールバック
  - MA200 等の計算で十分な履歴が無い場合、明示的に中立（例: ma200_ratio = 1.0）を用いる。
  - ai_scores / market_regime などの DB 書き込みは冪等性を考慮して実装（部分失敗時に既存データを不要に消さない）。

- .env 自動ロード
  - プロジェクトルート検出は __file__ の親ディレクトリを辿って .git または pyproject.toml の存在で判定します。配布後にルート検出が失敗する環境では自動ロードをスキップします。
  - OS 環境変数が優先されます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

- DuckDB 互換性
  - 一部の実装（executemany の空パラメータ不可への配慮等）は DuckDB のバージョン差分を考慮しています（例: executemany に空リストを渡さないガード）。

### マイグレーション / セットアップ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能を使う場合）
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 期待される DB テーブル（モジュール毎）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など

---

今後の予定（例）
- strategy / execution / monitoring サブパッケージの具体的な取引ロジック・発注連携の実装
- 単体・統合テストの追加と CI の整備
- モデル／プロンプト改良やトークン最適化（コスト削減）
- J-Quants クライアントまわりの例外処理やリトライのさらなる堅牢化

もし CHANGELOG に追加してほしい点（より詳細なモジュール別の変更履歴や抜けている注意点等）があれば教えてください。