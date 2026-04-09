CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠し、セマンティック バージョニングに従います。

フォーマット:
- Unreleased: 今後の変更
- 各リリース: 日付と変更カテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）

[Unreleased]
-----------

（なし）

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ情報:
    - src/kabusys/__init__.py にて __version__="0.1.0" を定義。
    - __all__ に data, strategy, execution, monitoring を宣言（将来的なサブパッケージ公開を想定）。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判定: .git または pyproject.toml を基準に探索（CWD に依存しない動作）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数を保護する protected 機構を実装し、.env の上書きを制御。
  - .env パーサーの実装:
    - export KEY=val 形式のサポート、クォート付き値のエスケープ処理、行末コメントの扱いなどを考慮。
  - Settings クラス（settings インスタンスを公開）:
    - J-Quants / kabu ステーション / LINE / DB パス / Paper Trading 設定など多数のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV および LOG_LEVEL の許容値チェックなどの妥当性検査。
    - is_live / is_paper / is_dev の簡易判定プロパティ。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news + news_symbols を用いて銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で解析し、ai_scores テーブルへ書き込み。
  - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB と比較）。
  - バッチ処理: 最大 20 銘柄/チャンク、1 銘柄当たりの記事数・文字数上限（トークン膨張対策）。
  - API 呼び出し: JSON Mode を利用、429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
  - レスポンス検証: JSON パース回復処理（前後余計テキストの補正）、results フォーマット検証、未知コードの無視、スコアの ±1.0 クリップ。
  - 書き込み戦略: 部分失敗時に既存の他コードスコアを保護するため、書き込み前に該当コードのみ DELETE → INSERT（DuckDB の互換性を考慮して executemany を使用）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
  - 処理フロー:
    - ma200_ratio の計算（target_date 未満のデータのみ使用、ルックアヘッド防止）。
    - raw_news からマクロキーワードに一致するタイトルを抽出して LLM に投げる。
    - OpenAI 呼び出しは専用関数で行い、リトライ・例外ハンドリングを実装（API失敗時は macro_sentiment=0.0 にフォールバック）。
    - 最終的な合成スコアを market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 設計上の注意:
    - datetime.today()/date.today() を参照せず、与えられた target_date に対して完全に決定的に動作する設計（ルックアヘッドバイアス対策）。
    - OpenAI API キーを引数または環境変数 OPENAI_API_KEY から解決。

- データ基盤ユーティリティ（src/kabusys/data/*）
  - calendar_management.py
    - JPX カレンダー（market_calendar）管理のユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録あり→DB 値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得・バックフィル・健全性チェック・保存）。
  - pipeline.py / etl.py
    - ETL の高レベル仕様と ETLResult データクラスを実装。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - ETLResult.to_dict() により品質問題を辞書化して出力可能。
  - jquants_client を前提とした差分取得 / 保存フローに対応する骨組みを実装（細部は jquants_client 側に依存）。

- リサーチ・ファクター（src/kabusys/research/*）
  - factor_research.py
    - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER/ROE）の計算関数を実装。
    - DuckDB を利用した SQL 集約で高速に計算。データ不足時の None ハンドリング。
    - 各関数は prices_daily / raw_financials のみを参照し、本番発注等にアクセスしない設計。
  - feature_exploration.py
    - 将来リターン計算（flexible horizons 対応）、IC（Spearman ランク相関）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。入力の検証（horizons 範囲等）を行う。

- パッケージ構成 / エクスポートの整備
  - kabusys.data.etl は ETLResult を再エクスポート。
  - kabusys.ai.__init__ で score_news を公開。
  - kabusys.research.__init__ で主な関数を再エクスポート（zscore_normalize は data.stats 由来）。

Security
- 本バージョンでは特にセキュリティ修正はなし。
- 注意点:
  - OpenAI API キー等の機密情報は環境変数で管理する想定。settings は必須キー未設定時に ValueError を投げるため、運用時は .env の管理に注意。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Deprecated
- （初回リリースのためなし）

Removed
- （初回リリースのためなし）

注記 / マイグレーション
- DuckDB のバージョン差異（特に executemany とリスト型バインドの扱い）を考慮した実装が行われています。DuckDB をアップデートする際は上述の部分（ai_scores の DELETE/INSERT 実装など）に注意してください。
- OpenAI の SDK や API の挙動（例: APIError の属性名変更等）に依存する箇所があるため、OpenAI SDK のメジャーアップデート時はエラーハンドリング部の確認が必要です。

以上。