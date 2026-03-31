# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
この CHANGELOG は、ソースコードの内容から推測できる機能追加・設計方針・注意点をもとに作成しています。

なおバージョン番号はパッケージ内の __version__ (0.1.0) を基にしています。

## [Unreleased]
- ドキュメント化や小さな改善・リファクタはここに記載します。

## [0.1.0] - 2026-03-31
初回リリース（推測）として以下の主要機能と設計方針を実装しました。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"、公開モジュール指定）

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）
  - export KEY=val 形式やクォート（シングル/ダブル）・エスケープシーケンス・インラインコメント処理に対応した .env パーサ実装
  - OS 環境変数の保護（読み込みの際に protected set を使用して上書き制御）
  - 自動ロード無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - Settings クラスによる環境変数ラップ（必須項目の検証、デフォルト値の提供、enum 検証）
  - DuckDB/SQLite のデフォルトパス設定（DUCKDB_PATH / SQLITE_PATH）

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (news_nlp)
    - raw_news / news_symbols からの銘柄別記事集約
    - OpenAI (gpt-4o-mini) を用いたバッチスコアリング（JSON Mode）
    - チャンク処理（デフォルト20銘柄/チャンク）、トークン肥大化対策（記事数・文字数制限）
    - 再試行（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（失敗時はスキップ）
    - レスポンスの厳密なバリデーションと ±1.0 クリップ
    - ai_scores テーブルへの冪等的な置換（DELETE → INSERT を用いた部分置換）
    - テスト容易性のため OpenAI 呼び出し内部関数を差し替え可能（unittest.mock.patch を想定）

  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して 'bull'/'neutral'/'bear' を日次判定
    - prices_daily / raw_news を参照してマクロキーワードによるフィルタ、OpenAI 呼び出し、スコア合成
    - API失敗時は macro_sentiment=0.0 のフェイルセーフ
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）および例外時の ROLLBACK 保護
    - LLM 呼び出しは独立実装でモジュール結合を避ける設計

- データプラットフォーム関連 (src/kabusys/data)
  - ETL パイプラインインターフェース (pipeline.py / etl.py)
    - 差分更新、バックフィル（デフォルト 3 日）、品質チェックのフレームワーク設計
    - ETLResult dataclass（実行メトリクス・品質問題・エラー保持、辞書化メソッド）
    - DuckDB を用いた最大日付検出ユーティリティ等

  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを用いた営業日判定・次/前営業日取得・期間営業日取得・SQ判定の実装
    - DB データがない場合の曜日ベースフォールバック（週末除外）
    - J-Quants からの差分取得ジョブ（calendar_update_job）とバックフィル・健全性チェック
    - _MAX_SEARCH_DAYS による探索上限と無限ループ防止

- リサーチ（因子・特徴量探索）モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を計算する関数群（calc_momentum / calc_volatility / calc_value）
    - DuckDB を用いた SQL ベースの計算で、本番の発注 API にはアクセスしない設計
    - データ不足時の None ハンドリング
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクタ要約統計（factor_summary）
    - pandas 等に依存しない純標準ライブラリ実装

- テスト性・堅牢性のための設計配慮
  - OpenAI 呼び出しを patch 可能にしてユニットテストで外部 API を模擬可能
  - ルックアヘッドバイアス対策: date.today() や datetime.now() の直接参照を避け、関数引数で基準日を受け取る設計（target_date を明示）
  - DB 書き込みはトランザクションを使用し、例外発生時にロールバック。部分失敗時に既存データを消さない配慮
  - API 応答のパース失敗や不整合は例外を上げずフォールバックやスキップで継続（フェイルセーフ）

### 変更点 (Changed)
- （初回リリースのため特になし）

### 修正 (Fixed)
- （初回リリースのため特になし）

### 削除 (Removed)
- （初回リリースのため特になし）

### 非推奨 (Deprecated)
- （初回リリースのため特になし）

### セキュリティ (Security)
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を使用。キーの自動出力やログへの漏洩に注意する実装方針。
- .env 読み込み時のファイル I/O エラーは警告に留めて処理を継続（ただしファイル権限等に注意）

---

注記:
- この CHANGELOG はコードベース（src 配下ファイル）の内容に基づき推測して作成しています。外部モジュール（jquants_client 等）の具象実装や追加のユーティリティはソースに依存します。必要であればさらにファイルごとの詳細な変更履歴や将来の改善案（例: OpenAI レスポンススキーマを型定義する、より細かなロギングレベル設定等）も追加できます。