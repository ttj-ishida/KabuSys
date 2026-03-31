# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

- フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回公開リリース。以下の主要機能・モジュールを実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み時の上書き制御 (override) と OS 環境変数保護（protected）をサポート。
  - .env パースの堅牢化：export プレフィックス、クォート／エスケープの扱い、インラインコメントの処理を実装。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）対応。
  - 必須環境変数取得時に明確なエラーメッセージを返す _require() を提供。
  - 設定ラッパークラス Settings を実装：
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。
    - KABUSYS_ENV の検証（development/paper_trading/live）や LOG_LEVEL の検証。
    - duckdb / sqlite のデフォルトパスや環境変数由来のパス解決。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄毎のセンチメントを算出。
    - バッチ処理（最大20銘柄 / チャンク）、1銘柄あたりの記事数上限・文字数トリム、JSON レスポンスの厳密バリデーションを実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフ戦略を実装。失敗時は当該チャンクをスキップして継続するフェイルセーフ設計。
    - AIレスポンスの数値スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
    - ルックアヘッドバイアスを防ぐため、内部で datetime.today()/date.today() を参照しない設計。
    - タイムウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30）を提供（calc_news_window）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日 MA 乖離 (重み 70%) と、マクロニュースの LLM センチメント (重み 30%) を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照し、OpenAI を用いてマクロセンチメントを取得（JSON パース、リトライ、5xx の扱いを考慮）。
    - API 障害時のフェイルセーフ（macro_sentiment = 0.0）や、データ不足時の中立デフォルト（ma200_ratio = 1.0）を実装。
    - 判定結果を market_regime テーブルへ冪等的にトランザクションで書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK）。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックを行う ETL の枠組みを実装。
    - ETL 結果を表現する dataclass ETLResult を提供（品質問題・エラーの収集、has_errors / has_quality_errors 等のユーティリティ）。
    - DuckDB による最大日付取得やテーブル存在チェック等のユーティリティ。
    - backfill の考慮、カレンダー先読み、品質チェック設計方針を反映。

  - 市場カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）を実装。J-Quants API 経由で market_calendar を差分取得・保存する処理を想定。
    - 営業日判定 API を提供：
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB の登録がある場合は DB 値を優先し、未登録日は曜日ベースでフォールバックする一貫性のある判定ロジックを実装。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェック（将来日付の異常検出）を実装。
    - jquants_client 経由の fetch / save 呼び出しを想定（外部クライアントに依存）。

  - ETL 公開インターフェース（kabusys.data.etl）
    - pipeline.ETLResult の再エクスポートを追加。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、結果を (date, code) をキーとする dict のリストで返す設計。
    - DuckDB のウィンドウ関数と SQL による効率的実装。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズンのサポート、入力検証）。
    - IC（Information Coefficient、スピアマンランク相関）の計算（calc_ic）。
    - ランク変換ユーティリティ（rank：同順位は平均ランク）。
    - ファクター統計サマリー（factor_summary：count/mean/std/min/max/median）。
    - pandas など外部ライブラリに依存しない純 Python 実装方針。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更点はなし（初稿）。

### 修正 (Fixed)
- 初期リリースのため過去バージョンからの修正点はなし（初稿）。

### 削除 (Removed)
- 該当なし。

### 非推奨 (Deprecated)
- 該当なし。

### セキュリティ (Security)
- OpenAI キー等の必須環境変数取得時に明確なエラーメッセージを出すことで誤構成に早期に気付けるよう配慮。

---

注意（設計上の重要ポイント／既知の振る舞い）
- API 呼び出し失敗時は例外を直ちに上位に伝播せず、該当処理をフェイルセーフに続行またはスキップする設計が多く採用されています（例: news_nlp・regime_detector）。運用時はログ監視や再試行設計が必要です。
- DB 書き込みは冪等性を意識した実装（DELETE→INSERT、トランザクション）になっています。DuckDB の executemany の空リスト挙動等の互換性を考慮したコードになっています。
- ルックアヘッドバイアス回避のため、内部処理は date/target_date ベースで実行し、実行時の現在時刻を直接参照しない設計方針を採用しています。
- OpenAI クライアント呼び出しはモジュール内部でラップしており、テスト時に差し替え可能です（単体テスト容易性を考慮）。

（以上）