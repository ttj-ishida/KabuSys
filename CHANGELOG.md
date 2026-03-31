# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

当リポジトリの現行バージョンはパッケージ定義 (src/kabusys/__init__.py) に基づき 0.1.0 です。

- [Unreleased]

- [0.1.0] - 2026-03-31
  - Added
    - 基本パッケージ構成
      - パッケージ名: kabusys、バージョン 0.1.0 を定義。
      - __all__ に data, strategy, execution, monitoring を公開する設計。
    - 環境設定モジュール (kabusys.config)
      - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
      - export KEY=val 形式やシングル/ダブルクォート、行内コメントの取り扱いに対応したパーサを実装。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 必須設定取得用の _require と Settings クラスを実装。J-Quants / kabuステーション / Slack / DB パス等をプロパティで取得。
      - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を追加。
    - AI関連モジュール (kabusys.ai)
      - ニュースNLP スコアリング (news_nlp)
        - raw_news と news_symbols を集約し、銘柄ごとに gpt-4o-mini を使ったセンチメント解析を行い ai_scores テーブルへ書き込む機能を実装。
        - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
        - バッチ処理（最大 20 銘柄）・1銘柄あたりの最大記事数／文字数トリム・JSON Mode レスポンス検証を実装。
        - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時は当該チャンクをスキップし処理継続（フェイルセーフ）。
        - レスポンス検証で未知コードの無視、スコアの ±1.0 クリップ、JSON の前後余計文字列の復元処理を実装。
      - 市場レジーム判定 (regime_detector)
        - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込む機能を実装。
        - マクロニュース抽出用のキーワードリストと、OpenAI（gpt-4o-mini）呼び出しによる macro_sentiment 評価を実装。
        - API 呼び出し失敗時のフォールバック（macro_sentiment=0.0）やリトライ、ログ出力を実装。
        - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試みる。
    - Research モジュール (kabusys.research)
      - ファクター計算 (factor_research)
        - Momentum: 約1/3/6ヶ月のリターン、200日 MA に対する乖離を計算する calc_momentum を実装（prices_daily を参照）。
        - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算する calc_volatility を実装。
        - Value: raw_financials と prices_daily を組み合わせて PER / ROE を計算する calc_value を実装（最新報告日ベース）。
        - DuckDB を用いた SQL 中心の実装で、外部 API へのアクセスは行わない設計。
      - 特徴量探索 (feature_exploration)
        - 将来リターン計算 calc_forward_returns（任意の営業日ホライズン）を実装。
        - Information Coefficient（スピアマン順位相関）を計算する calc_ic を実装。rank ユーティリティを提供。
        - factor_summary によりファクター列の基本統計（count/mean/std/min/max/median）を算出。
        - 外部ライブラリに依存せず標準ライブラリのみでの実装。
    - Data モジュール (kabusys.data)
      - カレンダー管理 (calendar_management)
        - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants API との連携を想定）。
        - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを実装。market_calendar が未取得の場合は曜日ベースでフォールバック。
        - 最長探索範囲やバックフィル日数など健全性チェックを組み込み。
      - ETL パイプライン (pipeline, etl)
        - ETLResult データクラスを公開し、ETL の取得数・保存数・品質検出結果・エラーを集約できるように実装。
        - 差分取得・バックフィル・品質チェックを行う設計（jquants_client と quality モジュールを利用）。
        - _get_max_date 等のヘルパーを実装し、テーブル存在チェックに対応。
      - data パッケージから ETLResult を再エクスポート。
  - Changed
    - 初期リリースのため該当なし。
  - Fixed
    - 初期リリースのため該当なし。
  - Removed
    - 初期リリースのため該当なし。
  - Notes / 注意事項
    - 環境変数（必須）
      - OPENAI_API_KEY（AI モジュール実行時、score_news / score_regime に必要）
      - JQUANTS_REFRESH_TOKEN（設定が必要な箇所あり）
      - KABU_API_PASSWORD, KABU_API_BASE_URL（kabu ステーション連携用）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用）
      - DUCKDB_PATH, SQLITE_PATH（デフォルトは data/ 配下）
      - KABUSYS_ENV（development / paper_trading / live）
    - データベース
      - 多くの処理は DuckDB 上のテーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime 等）を前提としているため、事前スキーマ準備が必要。
    - OpenAI 関連
      - gpt-4o-mini を想定（JSON Mode を利用）。API レスポンスの不整合に対する耐性（パース復元・検証）を実装。
      - テスト時の差し替えポイントとして _call_openai_api 関数を patch 可能に設計。
    - フェイルセーフ設計
      - LLM/API のエラーは可能な限り局所スキップやフォールバック（スコア 0.0 等）として継続する設計。
      - DB 書き込みは冪等性を考慮（DELETE → INSERT 等）している。
    - 時刻取り扱い
      - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接参照しない設計方針（対象日を引数で受け取る）。
    - 互換性 / 依存
      - DuckDB を前提とする実装。外部データ取得は jquants_client 等の別モジュールに委譲。
      - 外部ライブラリ（pandas 等）には依存しない設計。
    - 既知の制約
      - 一部の SQL バインド（DuckDB の executemany の空リスト問題）に対するワークアラウンドを含む実装があるため、古い DuckDB バージョンでの挙動に注意。
      - JSON モードでも稀に余計な文字列が混ざる可能性があるため、復元ロジックを導入しているが完全な安全性は保証しない。
  - Usage examples / 実行例（抜粋）
    - ニューススコアリング:
      - score_news(conn, target_date, api_key=None) -> 書き込み銘柄数
    - レジーム判定:
      - score_regime(conn, target_date, api_key=None) -> 1（成功）
    - 環境自動読み込みを無効化:
      - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Security
    - 初期リリースのため該当なし（ただし API キー等の取り扱いは環境変数・.env を利用。機密情報取扱いに注意）。

今後の予定（目安）
  - 単体テスト・統合テストの強化（特に OpenAI 呼び出しのモックを含む）。
  - 発注系（execution）・実稼働監視（monitoring）モジュールの実装・ドキュメント整備。
  - スキーマ定義・マイグレーション用スクリプトの追加。

（以上）