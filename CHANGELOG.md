# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載します。  
このファイルは、ソースコードから推測される実装内容・設計方針に基づいて作成しています。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコア機能群を提供します。主要な追加点と設計上の重要事項は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの公開APIを定義（data, strategy, execution, monitoring を __all__ に設定）。
  - バージョン情報 __version__ を "0.1.0" として設定。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み順序: OS 環境 > .env.local > .env、自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに配慮）。
  - 環境変数取得用 Settings クラスを提供（プロパティ: jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL などの許容値チェック）と必須環境変数チェック（未設定時は ValueError）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを付与して ai_scores テーブルへ書き込む機能（score_news）。
  - タイムウィンドウ計算（JST ベース）を行う calc_news_window を実装。
  - バッチ処理（最大 20 銘柄／API 呼び出し）、1 銘柄当たり記事数・文字数のトリミング制限を導入（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - OpenAI 呼び出しの堅牢化: レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ再試行、JSON Mode のレスポンス検証、部分失敗時の DB 保護（該当コードのみ DELETE→INSERT）。
  - レスポンス検証ロジック（results リスト、code/score の検証、スコアのクリップ、未知コードの無視）。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定し market_regime テーブルへ冪等書き込みする機能（score_regime）。
  - MA200 乖離計算（_calc_ma200_ratio）、マクロニュース抽出（_fetch_macro_news）、OpenAI への送信と再試行（_score_macro）を実装。
  - OpenAI 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
  - 出力のクリップとラベリング（bull / neutral / bear）、BEGIN / DELETE / INSERT / COMMIT による冪等性の確保。
  - LLM 呼び出しは別モジュールと分離した実装でモジュール結合を低減。

- データ基盤ユーティリティ（kabusys.data.*）
  - ETL インターフェースの公開（kabusys.data.etl が pipeline.ETLResult を再エクスポート）。
  - ETL 結果を表現する dataclass（ETLResult）を追加（取得数・保存数・品質問題・エラー一覧・ユーティリティメソッド to_dict(), has_errors, has_quality_errors）。
  - ETL パイプライン補助関数（テーブルの最大日付取得など）を実装。
  - 市場カレンダー管理モジュール（calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった営業日判定/取得関数を提供。
    - market_calendar が未取得時には曜日ベース（土日非営業）でフォールバック。
    - DB 登録値を優先し、未登録日は曜日フォールバックで補完する一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等更新（バックフィル・健全性チェックあり）。jquants_client 経由での取得/保存を想定。

- リサーチ機能（kabusys.research.*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB の SQL ウィンドウ関数で計算。
    - calc_volatility: 20 日 ATR（true range の扱いに注意）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務を取得して PER / ROE を算出（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを LEAD を用いて一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（None/不足レコードの除外、最小要件 3 件）。
    - rank: 同順位は平均ランクを返す実装（round による ties 対策）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出。
  - 上記は外部ライブラリに依存せず、DuckDB と標準ライブラリのみで実装。

- API クライアント挙動
  - OpenAI クライアント（OpenAI(api_key=...)）を利用し、JSON Mode（response_format={"type":"json_object"}）を想定した厳密なレスポンス処理を行う。
  - 再試行・バックオフ・エラー種別別の扱い（RateLimitError, APIConnectionError, APITimeoutError, APIError の区別）を実装。

### Changed
- （初回リリースのため過去の変更はありません）

### Fixed
- （初回リリースのため過去のバグ修正履歴はありません）

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策
  - 全 AI/リサーチ関連処理で datetime.today() / date.today() を直接参照しない設計を明記（target_date ベースで計算）。
  - prices_daily 等のクエリで target_date 未満・排他条件を用いるなど、未来情報の混入を防止。

- データベース操作の冪等性と部分失敗保護
  - market_regime / ai_scores / ETL の DB 書き込みは DELETE→INSERT（BEGIN/COMMIT）や個別 DELETE の executemany を用い、部分失敗時にも既存データを不必要に消さない工夫あり。
  - DuckDB のバージョン差分への互換性（executemany の空リスト制約など）に対応した実装。

- フェイルセーフ
  - 外部 API（OpenAI, J-Quants）失敗時は、致命的に停止させずフェイルセーフ（デフォルトスコア・スキップ・警告ログ）で継続する方針。

- ロギング
  - 各主要処理に debug/info/warning/exception ログを散りばめ、運用時のトラブルシュートを容易にする設計。

### Security
- セキュリティに関する特記はなし（環境変数で API キーを扱う設計）。運用時は secrets 管理とアクセス制御を推奨。

---

今後のリリースでは、strategy / execution / monitoring の具現化、単体テストと CI の整備、ドキュメント強化（API 使用例・migration 手順）などが想定されます。必要であれば、この CHANGELOG をさらに細分化してコミットや PR ベースの履歴へ落とし込む手助けをします。