# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルではリポジトリ内のソースコードから推測される主要な機能追加・仕様・設計方針を記載しています。

注: 実装から推測して記載しているため、実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

（現在のツリーに対する未リリースの変更はありません）

## [0.1.0] - 2026-03-27

初回公開リリース。日本株自動売買システムの基盤となる以下機能群を実装・公開しました。

### Added

- パッケージ基盤
  - 初期パッケージ定義（kabusys）とバージョン情報を追加（src/kabusys/__init__.py）。
  - パッケージの公開 API（data, research, ai 等）を整理。

- 設定管理
  - 環境変数 / .env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - .git または pyproject.toml を基準にプロジェクトルートを自動検出。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - export KEY=val 形式、クォート処理、インラインコメント処理に対応した .env パーサー。
    - 既存 OS 環境変数を保護する protected 機構と override オプション。
  - Settings クラスでアプリ設定を集中管理（J-Quants / kabu / Slack / DB パス / 環境 / ログレベル等）。
    - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - KABUSYS_ENV の許容値（development, paper_trading, live）と LOG_LEVEL 検証。
    - duckdb/sqlite パスのデフォルト値を設定。

- データ基盤（DuckDB ベース）
  - ETL パイプラインの基礎（src/kabusys/data/pipeline.py）
    - 差分取得、バックフィル、品質チェックの設計。
    - ETLResult データクラス（実行結果・メタ情報・品質問題・エラー集約）。
    - テーブル存在チェックや最大日付取得ユーティリティ。
  - ETL の公開インターフェース（src/kabusys/data/etl.py: ETLResult の再エクスポート）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を元に営業日判定・前後営業日取得・期間内営業日列挙・SQ判定 API を実装。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job による J-Quants からの差分フェッチと冪等保存（バックフィル・健全性チェック含む）。
  - jquants_client 経由でのデータ取得／保存を想定した設計（外部クライアントは別モジュールとして想定）。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離）
    - Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比）
    - Value（PER、ROE） — raw_financials からの財務データ参照
    - DuckDB のウィンドウ関数を用いた効率的実装とデータ不足時の安全処理（None 返却）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（スピアマンランク相関）
    - ランク変換ユーティリティ（同順位は平均ランク）
    - ファクター統計サマリー（count/mean/std/min/max/median）
  - research パッケージの公開 API を整理（__init__ で各関数をエクスポート）。

- ニュース NLP / AI 機能
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウを計算する calc_news_window。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数トリム対応）。
    - バッチ（最大 20 銘柄）で OpenAI（gpt-4o-mini）に送信し JSON mode でスコアを取得。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーションと数値スコアの ±1.0 クリップ。
    - 成功分のみ ai_scores テーブルを置換（DELETE → INSERT）して部分失敗で既存データを保護。
    - テスト容易性のため OpenAI 呼び出し箇所を差替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
    - マクロニュースは raw_news からキーワードフィルタして取得（最大 20 件）。
    - OpenAI を使った JSON 出力のパース、リトライ（429/ネットワーク/5xx）とフォールバック macro_sentiment=0.0。
    - スコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス回避のため datetime.today() を直接参照しない設計。
  - ai パッケージで score_news を公開（src/kabusys/ai/__init__.py）。

- 互換性・安全性・運用設計
  - 全体を通して「ルックアヘッドバイアスを避ける」設計（datetime.today()/date.today() に依存しない）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定など）。
  - エラー耐性: API 呼び出し失敗は基本的に例外で止めずフォールバックまたはスキップして継続する方針。
  - DuckDB のバージョン差分（executemany の空リスト制約等）を考慮した実装ワークアラウンドあり。
  - ロギングを随所に導入（INFO/WARNING/DEBUG）し、問題時の調査を容易化。

### Changed

- 初回リリースのため該当なし。

### Fixed

- 初回リリースのため該当なし。

### Security

- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を送出して明示的にエラー化。

### 締めと注意事項

- 必要な外部環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- DuckDB に期待するテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が前提です。実行前にスキーマ準備を行ってください。
- OpenAI の呼び出しは gpt-4o-mini + JSON mode を前提にしており、API レスポンス形式の変化に注意してください。
- 実稼働での利用（特に live 環境）はリスクがあるため、まずは paper_trading / development で十分に検証してください（Settings.is_live / is_paper / is_dev を利用）。

---

[0.1.0]: https://example.com/releases/0.1.0 (初回リリース)