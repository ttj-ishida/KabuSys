# Changelog

すべての重要な変更履歴をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-31

初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名 kabusys を追加。公開 API として data / strategy / execution / monitoring を __all__ で定義。
  - バージョン管理: __version__ = "0.1.0"。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をサーチして自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env ファイル行パーサ（コメント、export プレフィックス、シングル/ダブルクォートおよびバックスラッシュエスケープに対応）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などをプロパティ経由で取得できるようにした。
  - 必須環境変数未設定時に ValueError を送出する _require ヘルパーを実装。
  - LOG_LEVEL / KABUSYS_ENV のバリデーションを追加。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に JSON モードで送信してセンチメント（-1.0〜1.0）を取得し ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST を対象（UTC に変換して DB クエリ実行）。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数の上限設定（記事数: 10、文字数: 3000）。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、各要素の code/score チェック、スコアの数値化と ±1.0 クリップ）。
    - DuckDB の executemany の制約（空リスト不可）に配慮した DB 書き込みロジック（DELETE → INSERT、部分的な書き込みで既存データを保護）。
    - API 呼び出し箇所はテスト容易性のため内部で差し替え可能な _call_openai_api を定義。

  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルに保存する処理を実装。
    - ma200_ratio の計算は target_date 未満のデータのみを用いることでルックアヘッドバイアスを防止。
    - マクロ記事が存在する場合にのみ LLM 呼び出しを行い、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - OpenAI SDK の APIError 等に対する細やかなエラーハンドリングとリトライを実装。
    - 書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）を行い、失敗時は ROLLBACK を試みる。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルに基づく営業日判定ユーティリティ群を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した設計。
    - calendar_update_job を実装し、J-Quants クライアント経由でカレンダーの差分取得・保存を行う（バックフィル・健全性チェック付き）。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開。ETL の取得数・保存数・品質チェック結果・エラーを保持し、dict 変換をサポート。
    - 差分取得、backfill、品質チェック（quality モジュール）を想定した設計を実施。
    - jquants_client を利用した idempotent 保存やエラーハンドリングの実装方針を文書化。
  - data パッケージの公開インターフェース整備（etl の ETLResult を再エクスポート）。

- リサーチ・解析ツール (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等の定量ファクターを DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - prices_daily / raw_financials テーブルのみ参照し、副作用を持たないよう設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン算出（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 非依存で純標準ライブラリ + DuckDB による実装。
  - research パッケージで主要関数を __all__ にて公開。

- テスト・運用を意識した実装上の配慮
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() の直接参照を避け、関数呼び出し側から target_date を受け取る設計。
  - OpenAI 呼び出し処理をモック差し替え可能にしてユニットテストを行いやすくした（内部 _call_openai_api を patch 可能）。
  - DuckDB 固有の挙動（executemany の空リスト禁止）に対応した実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- DB トランザクション失敗時の ROLLBACK 試行とログ出力を追加し、ROLLBACK 失敗時も上位へ例外を伝播するようにした（安全なクリーンアップ）。

### Security
- 環境変数の必須チェックを厳格化（OpenAI API キー、SLACK トークン等）。未設定時は ValueError を送出して早期検出可能にした。
- .env 読み込み時に OS 側の既存環境変数を保護する仕組み（protected keys）を導入。

### Notes / Known limitations
- OpenAI を使う機能は実運用時に API キー（OPENAI_API_KEY）を必要とする。キー未設定だと score_news / score_regime は ValueError を送出する。
- モデル指定は gpt-4o-mini を前提とする。将来の SDK 変更に備え、APIError の status_code を getattr で安全取得する実装をしているが、SDK の大幅な変更時は追加対応が必要。
- news_nlp と regime_detector は LLM 呼び出しロジックを独立させている（モジュール間でプライベート関数共有しない）ため、差し替え・テストが容易。
- DuckDB のバージョン差異に起因する SQL バインド動作（リストバインド等）に対して、互換性を優先した実装を行っている（executemany による個別 DELETE 等）。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）の実装に依存するため、クライアントの挙動に応じた運用が必要。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡張（発注・監視ロジック）。
- 単体テスト・統合テストの追加カバレッジ強化。
- OpenAI 呼び出しのコスト最適化やキャッシュレイヤの導入。

（以上）