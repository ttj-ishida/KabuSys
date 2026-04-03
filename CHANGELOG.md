# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03
初回リリース — 日本株自動売買・データ基盤のコアライブラリの初期実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。パッケージの公開 API として data, strategy, execution, monitoring を想定。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して決定（CWD に依存しない実装）。
  - .env パーサを細かく実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱い等に対応）。
  - 自動読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - OS 環境変数を保護するため `.env.local` 読み込み時の上書き保護ロジックを実装。
  - Settings クラスを提供し、API キー・DB パス・監視閾値・ログレベル等の設定をプロパティ経由で取得可能に（必須キー取得時の例外送出を含む）。
  - 有効な環境 (`KABUSYS_ENV`) 値検証（development / paper_trading / live）およびログレベル検証を実装。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を元にニュース記事を銘柄単位で集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（1回あたり最大20銘柄）、記事数/文字数上限（銘柄毎の最大記事数・トリム長）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフ リトライを実装。その他のエラーはスキップしてフェイルセーフに継続。
    - レスポンスバリデーション（JSON 抽出、results リスト形式、コード照合、数値チェック）実装。スコアを ±1.0 にクリップ。
    - DuckDB へは ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込む。部分失敗時に既存データを保護するため書込対象コードを限定。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch 可能）。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - regime_detector モジュール
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの ma200 乖離計算（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用）。
    - raw_news からマクロキーワードでタイトルを抽出し、OpenAI によりマクロセンチメントを算出（記事が無ければ LLM 呼ばずに 0.0 を採用）。
    - OpenAI 呼び出しはリトライ・バックオフ対応、API 失敗時は macro_sentiment=0.0 でフォールバック（例外は投げない）。
    - スコア合成後、market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - テスト容易性のため API キー注入可能。公開 API: score_regime(conn, target_date, api_key=None)

- データ基盤モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理機能（market_calendar）を提供：営業日判定、次/前営業日取得、期間内営業日取得、SQ 日判定。
    - DB の market_calendar がない/未登録日の場合は曜日ベース（平日＝営業日、土日＝非営業日）でフォールバック。
    - 最長探索日数制限（_MAX_SEARCH_DAYS）を設け無限ループを防止。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - J-Quants クライアント呼び出しを jquants_client に委譲。

  - pipeline / etl
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー情報等を保持、辞書化メソッドを提供）。
    - ETL パイプラインの骨子（差分更新、バックフィル日数、品質チェックの扱い、id_token 注入によるテスト容易化等）を実装方針として整備。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得等）を用意。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER/ROE）等のファクター計算機能を実装。
    - DuckDB を利用した SQL ベースの計算（prices_daily / raw_financials を参照）で、ルックアヘッド回避の設計を採用。各関数は (date, code) をキーとする dict のリストを返す。
  - feature_exploration モジュール
    - 将来リターン計算（horizons の任意指定）、IC（Spearman）計算、値のランク変換、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。入力検証（horizons の範囲等）を実施。

- テスト/運用を意識した設計上の実装
  - ルックアヘッドバイアス回避の徹底（datetime.today()/date.today() を内部で参照しない設計方針を各所で採用）。
  - OpenAI 呼び出し箇所は差し替え可能（テスト時のモック化を想定）。
  - API 障害時のフェイルセーフ（デフォルトスコアやスキップ処理）を多くの箇所で取り入れ、部分障害が全体を止めない方針。
  - DuckDB に対する executemany の空リスト問題など実運用での互換性を考慮した実装（空チェックを明示）。

### 変更 (Changed)
- N/A（初回リリース）

### 修正 (Fixed)
- N/A（初回リリース）

### 削除 (Removed)
- N/A（初回リリース）

### セキュリティ (Security)
- 環境変数読み込みで OS 環境変数を保護する仕組みを採用（.env.local で既存 OS 環境を不用意に上書きしない）。

---

備考:
- 本リリースはライブラリのコアな初期機能群の整備に焦点を当てています。実際の運用には J-Quants / kabuAPI 等の外部サービス設定、OpenAI API キーなどの環境設定が必要です。.env.example を参照して環境変数を準備してください。