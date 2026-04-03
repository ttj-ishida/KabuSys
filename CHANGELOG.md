# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、本CHANGELOGはリポジトリの現行コードベースから機能・設計方針を推測して作成した初期リリース向けの要約です。

## [Unreleased]

- （現状なし）

## [0.1.0] - 2026-04-03

初回リリース。以下の主要コンポーネントを実装・公開。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで `data`, `strategy`, `execution`, `monitoring` をエクスポート（__all__）。
  - パッケージバージョンを `0.1.0` として定義。

- 設定 / 環境変数管理
  - robust な .env 読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env のパースは `export KEY=val`、単/二重クォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - 既存 OS 環境変数保護（protected set）を考慮した上書き制御。
  - Settings クラスを提供（settings オブジェクト経由で利用）。主な設定:
    - J-Quants / kabuステーション / LINE API のトークン・URL
    - DB パス (duckdb / sqlite)・監視用ファイルパス
    - CPU/Memory/Disk 閾値
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション
    - is_live / is_paper / is_dev のショートカットプロパティ
  - 必須環境変数未設定時は `_require` が ValueError を送出することで明示的に失敗させる設計。

- AI モジュール（OpenAI 統合）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から指定ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を抽出する calc_news_window を実装。
    - 各銘柄ごとに記事を集約し、1銘柄当たりの最大記事数・文字数制限を適用して OpenAI（gpt-4o-mini）の JSON モードでバッチ送信。
    - バッチ処理サイズ、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）とレスポンス検証ロジックを実装。
    - レスポンスのバリデーション（JSON 抽出、"results" の存在、code/socre の検証、スコアクリップ ±1.0）。
    - 書き込みは部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT の冪等更新を行う。
    - テスト容易性のために _call_openai_api をモック差し替え可能な設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行う score_regime を実装。
    - prices_daily からの MA200 計算はルックアヘッドを防ぐため target_date 未満のデータのみを使用。
    - raw_news からマクロキーワードでタイトルを抽出し、OpenAI（gpt-4o-mini）の JSON レスポンスをパース。
    - API エラー時は安全側（macro_sentiment = 0.0）で継続するフォールバックを採用。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に処理。失敗時は ROLLBACK。

- データ基盤（DuckDB ベース）
  - ETL パイプライン基礎（src/kabusys/data/pipeline.py と etl の再エクスポート）
    - 差分取得、idempotent 保存（jquants_client 経由）、品質チェック（quality モジュールとの連携）を想定した ETLResult データクラスを実装。
    - backfill（再取得）やカレンダ先読みを考慮した設計。
    - エラー・品質問題を収集して呼び出し元で判断する方針（Fail-Fast ではない）。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを元に営業日判定/前後営業日取得/get_trading_days/is_sq_day 等のユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業）でフォールバックする一貫した設計。
    - calendar_update_job により J-Quants から差分取得・バックフィル・保存を行う。取得結果が空や API エラー時は 0 を返す設計。
    - 最大探索日数や健全性チェック（未来日付の異常検出）等を導入して無限ループや異常データを防止。

- リサーチ / ファクター計算
  - ファクター計算群（src/kabusys/research/*）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB SQL で計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データと価格を組み合わせて PER/ROE を算出（EPS が 0 または欠損の場合は None）。
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得する効率的クエリ。
    - calc_ic / rank / factor_summary: IC（Spearman）計算、同順位平均ランク処理、記述統計（count/mean/std/min/max/median）を実装。
  - 実装上の方針:
    - DuckDB 接続を受け、SQL と標準ライブラリで完結。外部依存（pandas など）を避ける。
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を内部で参照しない。

### 改良 (Changed)

- なし（初回リリースのため）。

### 修正 (Fixed)

- なし（初回リリースのため）。

### セキュリティ (Security)

- OpenAI API キーは引数注入または環境変数（OPENAI_API_KEY）で解決。未設定時は ValueError を送出して明示的に失敗させる。
- .env の自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 注意事項 / マイグレーションノート

- DuckDB の executemany に空リストを渡すとエラーになる古いバージョンの互換性（0.10 系）に配慮して、空チェックを行ってから executemany を呼ぶ実装になっています。環境の DuckDB バージョン次第で注意してください。
- OpenAI とのやり取りはモデル gpt-4o-mini を想定した JSON Mode を利用します。API レスポンスの変化に対してはフォールバック（スコア=0.0）やレスポンスパースの堅牢化処理を入れていますが、外部 API の仕様変更には追従が必要です。
- market_calendar が未登録の場合、関数は曜日ベースでフォールバックします。カレンダーデータの取得を運用で確実に行ってください。
- settings の KABUSYS_ENV / LOG_LEVEL は許容値チェックを行い、不正値で ValueError を送出します。CI / デプロイ時に注意してください。

---

（この CHANGELOG はコード内容からの推測に基づいて作成しています。実際のリリース・変更履歴として公開する場合は、必要に応じて日付や担当者、リリース手順等を追記してください。）