# CHANGELOG

すべての重要な変更点はこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。

なお、本CHANGELOGはソースコードからの推測に基づき作成しています。

## [Unreleased]

### 追加
- 主要モジュールの骨組みを追加（kabusys パッケージ初期実装）。
  - 公開 API: kabusys.__version__ = 0.1.0、サブパッケージとして data / research / ai / monitoring などを想定。
- 環境設定管理（kabusys.config）を実装。
  - .env / .env.local の自動ロード機能（OS 環境変数優先、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 複雑な .env パース機能（export 文対応、クォート内のエスケープ、インラインコメント取り扱い）。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
  - 必須環境変数未設定時に明示的な ValueError を発生させる _require。

- データプラットフォーム関連（kabusys.data）を実装。
  - カレンダー管理（calendar_management）
    - market_calendar テーブルに基づく 営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェック。
    - 夜間バッチ job（calendar_update_job）で J-Quants から差分取得→保存を行う想定（jq クライアント経由）。
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラス（実行結果・品質問題・エラー集約）。
    - 差分取得、保存（idempotent 保存想定）、品質チェックの枠組み（quality モジュール連携を想定）。
    - DuckDB を主要な一時 DB として利用する設計。

- 研究（research）モジュールを実装。
  - factor_research
    - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性指標、バリュー指標（PER/ROE）を計算する関数を用意。
    - DuckDB SQL を活用した計算で、結果を (date, code) キーの辞書リストで返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付け（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリで実装（テスト容易性を重視）。

- AI（kabusys.ai）機能を実装。
  - ニュース NLP（news_nlp）
    - 指定時間ウィンドウ内の raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_scores）を取得して保存する流れを実装。
    - バッチサイズ、記事数・文字数のトリム、JSON モードのレスポンスバリデーション、スコアクリップ（±1.0）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで処理し、失敗時は該当チャンクをスキップして他チャンクは継続するフェイルセーフ設計。
    - テスト用フック: _call_openai_api を patch 可能。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し、OpenAI API 呼び出し時は再試行ロジックを実装。API 失敗時は macro_sentiment = 0.0 で継続するフェイルセーフ。
    - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアスを防ぐ設計（datetime.today() 等を参照せず、DB クエリに date < target_date の排他条件を使用）。

### 変更
- なし（初期リリースのため該当なし）。

### 修正
- なし（初期リリースのため該当なし）。

### 既知の制限 / 注意事項
- OpenAI の API キーは api_key 引数または環境変数 OPENAI_API_KEY で渡す必要がある。未設定時は ValueError を送出。
- OpenAI への実際の呼び出しは gpt-4o-mini を想定（response_format に JSON mode を使用）。
- DuckDB に依存した SQL 実装が多く、DuckDB のバージョン依存（executemany の空リスト不可等）に配慮した実装が含まれている。
- タイムウィンドウはUTC naive datetime で扱う箇所があり、JST ↔ UTC の変換ルールがコード内に明示されている（news ウィンドウ等）。
- テスト容易性のため、API 呼び出し箇所はモック / patch しやすいよう設計されている（内部関数名が明示的）。
- 本リリースでは一部の指標（PBR・配当利回り等）は未実装。

---

## [0.1.0] - 2026-04-03

初回公開リリース。上記「Unreleased」に記載の機能群を提供。

### 追加
- パッケージ初期実装（環境設定、データ ETL / カレンダー管理、研究用ファクター計算、特徴量解析、AI を用いたニュースセンチメント評価、レジーム判定、ETL 結果データ構造）。
- ロバストネス設計:
  - API 呼び出しの再試行とフォールバック（OpenAI / J-Quants / ネットワーク障害への耐性）。
  - DB 書き込みは冪等操作（DELETE→INSERT、トランザクションの使用、ROLLBACK 処理）。
  - ルックアヘッドバイアス防止の設計方針を各所で適用。
- 設定管理: .env/.env.local の自動ロード、各種デフォルト値、検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

### 既知の制限 / 注意事項
- 実行には OpenAI API キーや J-Quants 等の外部 API 認証情報が必要。
- 実データ保存先として DuckDB を想定（デフォルトパスは data/kabusys.duckdb）。
- 初期実装のため追加のエラーハンドリングや運用監視フローは今後改善予定。

---

（以降のバージョンでは機能追加・バグ修正・破壊的変更等をここに記載します。）