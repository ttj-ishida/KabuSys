# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはリポジトリのコードを元に推測して作成しています（実装済み機能・設計方針の要約）。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-03

初回リリース（推測）。日本株自動売買 / データ基盤 / 研究・AI モジュールの骨格を実装。

### Added
- パッケージ基礎
  - kabusys パッケージの初期設定（src/kabusys/__init__.py）。バージョン `0.1.0` を定義し、主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定管理
  - 環境変数・.env 読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動 .env ロードを実現。
    - .env/.env.local の優先順位を実装（OS 環境変数 > .env.local > .env）。override/protected 機能を備え、OS 環境変数の保護に対応。
    - .env パースは export プレフィックス、クォート文字、エスケープ、インラインコメント処理等の細かな仕様に対応。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスに主要設定プロパティを公開（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定等）。
    - 必須環境変数チェック（_require）で設定不足時に明示的なエラーを送出。
- AI 関連（ニュース NLP / 市場レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信。
    - バッチ処理（最大 20 銘柄/回）、JSON レスポンス検証、スコア ±1.0 でクリップ、部分失敗時に既存データを保護する DB 書き込み（DELETE → INSERT）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。重大な API エラー時はスキップするフェイルセーフ方針。
    - ルックアヘッドバイアス防止のため datetime.today() を参照せず、target_date ベースでウィンドウ計算（calc_news_window）を行う。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（関数単位で patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を判定・保存。
    - マクロニュース抽出はキーワードベース（複数キーワード定義）でタイトルをフェッチし、OpenAI により JSON スコア（{"macro_sentiment": ...}）を取得。
    - OpenAI API 呼び出しは独立実装でモジュール結合を避ける。API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - 計算結果は冪等的に market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新財務データを取得して PER/ROE を算出（EPS が無効なら PER は None）。
    - DuckDB を用いた SQL ベースの計算。結果は (date, code) を含む dict のリストとして返却。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）のリターンを取得。horizons 引数に対するバリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関を実装し、データが不足する場合は None を返す。
    - ランク化ユーティリティ（rank）とファクター統計サマリ（factor_summary）を提供。外部ライブラリに依存しない実装。
  - research パッケージの公開関数を __all__ で整理。
- データ基盤（Data）モジュール
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの有無に応じた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job を実装し、J-Quants からの差分フェッチ → 保存（保存関数は jquants_client に委譲）を行う。バックフィル・健全性チェックあり。
  - ETL パイプライン骨格（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を導入（取得件数・保存件数・品質問題リスト・エラーリスト等を保持）。
    - 差分更新・バックフィル・品質チェック・idempotent な保存（jquants_client の save_* を期待）を設計方針として明記。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得等）を実装。
  - jquants_client のクライアント参照（calendar_management からの利用を確認）。
- 監視・実行関連（設計・設定）
  - Settings に監視用ファイルパス（PID/KILL flag）やリソース閾値（CPU/Memory/Disk）を定義。kill flag の自動クリア設定を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー取り扱い
  - API キーは関数引数で注入可能。環境変数 OPENAI_API_KEY をデフォルト参照。未設定時は明示的に ValueError を投げることでキー漏洩や誤用を早期に検出。

### Notes / 設計上の重要事項（実装ドキュメント的記載）
- ルックアヘッドバイアス対策: AI モジュール（news_nlp, regime_detector）・score_news/score_regime 等は内部で datetime.today() を参照せず、必ず caller が与える target_date に基づいてウィンドウを計算する設計。
- フェイルセーフ: LLM/API の障害時は大局的な失敗を避けるためデフォルト値（例: macro_sentiment=0.0）で継続し、ログに警告を出力。DB 書き込み失敗時はトランザクションをロールバックして例外を伝播。
- テスト容易性: OpenAI 呼び出しポイントはモジュール内で明確に切り出されており、unittest.mock.patch による差し替えが可能。
- DuckDB を一次データストアとして想定し、SQL + Python の組合せで高パフォーマンスにデータ処理を行う設計。
- DB 書き込みは冪等化を重視（DELETE → INSERT、ON CONFLICT の想定等）。部分失敗があっても既存データを不必要に消さない実装方針。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する場合は、追加の変更点（strategy / execution / monitoring 実装状況、jquants_client の実装詳細、互換性情報など）を追記してください。