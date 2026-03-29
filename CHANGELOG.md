CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-------------

（現在のリポジトリは初回リリース相当の内容のため、以下は初版の変更点です）

0.1.0 - 2026-03-29
------------------

### Added
- 初回リリース: kabusys パッケージ (バージョン 0.1.0)
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring（__all__ 宣言）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルの自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理、無効行スキップ等に対応。
  - .env.local が .env を上書きする挙動（OS 環境変数は protected として上書き回避）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス等のプロパティを提供（環境変数必須チェックとデフォルト値、KABUSYS_ENV / LOG_LEVEL の検証など）。
  - 必須環境変数未設定時は明示的な ValueError を送出。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON mode）でバッチセンチメント評価。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数と文字数制限（トリム）を実装。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ。
    - レスポンスの堅牢なバリデーション（JSON 抜き出し、results 配列チェック、コード照合、数値有効性、±1.0 でクリップ）。
    - DuckDB 上の ai_scores テーブルへ差分置換（DELETE → INSERT）を行い、部分失敗時に他銘柄データを保護。
    - lookahead バイアス回避のため内部で datetime.today()/date.today() を参照しない設計。
    - OpenAI キー注入（api_key 引数 or OPENAI_API_KEY 環境変数）。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離(ma200_ratio) と、マクロニュースの LLM センチメントを重み付け合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、最大 20 記事を LLM に供給。
    - レジームスコア合成(重み: MA 70% / Macro 30%)、閾値に基づくラベリング。
    - API 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - idempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar がない場合は曜日ベースでフォールバック（週末除外）。
    - 夜間バッチ calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新、バックフィルと健全性チェック機構を実装。
    - DuckDB の日付データ型を扱うためのユーティリティ関数を提供。

  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得ロジック、最終日取得ユーティリティ、品質チェック結果の収集・報告を想定した設計ドキュメントに準拠した実装（jquants_client 経由での保存呼び出しを前提）。

- 研究用ユーティリティ (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照。SQL ウィンドウ関数を活用）。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary（将来リターン、Spearman IC、ランク付け、統計サマリ）。
  - zscore_normalize を data.stats から再エクスポート。
  - None 値・データ不足の取り扱い、営業日スキャン範囲のバッファなどを考慮した実装。

### Fixed / Robustness
- AI モジュール・データモジュール共通の改善点:
  - ルックアヘッドバイアス防止のため、内部ロジックで現在日時を直接参照しない実装（target_date ベースの計算）。
  - OpenAI API 呼び出しの失敗に対する堅牢なハンドリング（リトライ・バックオフ・5xx の取り扱い、非致命化してゼロスコアで継続するフェイルセーフ）。
  - DuckDB の executemany に対する互換性問題（空リストを渡さないガード）を考慮した実装。
  - OpenAI SDK の将来の変化（status_code の有無など）に耐えるため getattr を利用した安全なエラーハンドリング。
  - DB 書き込み時のトランザクション保護（ROLLBACK の失敗時に警告ログ）。

### Security / Configuration
- 環境変数の扱いに関する注意:
  - 必須トークン（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）は Settings で明示的にチェックし、未設定時は ValueError を送出。
  - OS 環境変数はデフォルトで保護される挙動（.env による上書きを防止）。
  - 自動環境ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを提供。

### Notes / Known limitations
- 外部依存:
  - OpenAI API を利用する部分は外部サービスに依存するため、API キーとネットワーク接続が必要。ローカルテストでは _call_openai_api をモックすることを想定。
  - J-Quants クライアント（jquants_client）への依存を想定したコード箇所あり（calendar_update_job / pipeline）。
  - DuckDB を用いる設計のため、DuckDB のバージョン差異に起因する挙動の違いに注意（特に executemany の挙動）。

- 未実装 / 将来対応想定:
  - 一部の指示書に記載される拡張項目（PBR・配当利回り等のバリューファクター拡張）は現バージョンでは未実装。
  - strategy / execution / monitoring モジュールの実装はパッケージ公開に含まれるが、今回のコードベースでは詳細実装が限定的（今後の追加を想定）。

References
----------
- プロジェクト内各モジュールに詳細な設計方針・処理フローの docstring を記載（各ファイル参照）。
- 本 CHANGELOG はコード内容から推測して作成しているため、実際のコミット履歴と差異がある場合があります。