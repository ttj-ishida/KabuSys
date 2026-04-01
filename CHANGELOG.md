# Changelog

すべての重要な変更はこのファイルに記載します。本プロジェクトは Keep a Changelog のフォーマットに準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-01

初回公開リリース。以下の主要機能と実装方針を含みます。

### 追加 (Added)

- パッケージ基礎
  - パッケージ初期化: kabusys モジュールのエントリポイントを追加（__version__ = 0.1.0, __all__ に data, strategy, execution, monitoring を公開）。

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない動作）。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - .env 読み込み時に既存 OS 環境変数を保護する仕組み（protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途）。
  - .env パースの柔軟化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い、無効行のスキップ。
  - 必須環境変数チェック用ヘルパー _require と Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定などのプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の値検証ロジックを含む（許容値チェック）。
    - Path 型戻りや float 変換などのユーティリティ的プロパティを実装。

- AI（NLP）機能 (src/kabusys/ai/)
  - ニュースセンチメントスコアリング (news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini の JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄／件）、1 銘柄あたりの記事数上限・文字数トリム、JSON レスポンスの厳格検証・クリッピング（±1.0）。
    - Retry（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。失敗時は安全にスキップし処理継続（フェイルセーフ）。
    - テスト容易化のため _call_openai_api の差し替えを想定（unittest.mock.patch）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF（1321）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算。
    - prices_daily / raw_news / market_regime テーブルを用いて冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しのリトライ/バックオフ、API 失敗時の macro_sentiment=0.0 フェイルセーフ、OpenAI クライアントの直接生成（モジュール結合回避）を実装。
    - ルックアヘッドバイアス対策: date パラメータに依存し、datetime.today()/date.today() を直接参照しない実装方針を採用。

- データプラットフォーム (src/kabusys/data/)
  - カレンダー管理 (calendar_management.py)
    - JPX マーケットカレンダーの夜間バッチ更新 job（calendar_update_job）と、営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（平日のみ）でフォールバックする一貫した挙動。
    - データ保全のため最大探索日数や健全性チェック、バックフィルロジックを実装。
  - ETL パイプライン基盤 (pipeline.py, etl.py)
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー集約を保持）。
    - 差分取得、保存（idempotent な保存を想定）、品質チェックのフロー設計に基づくユーティリティを実装。
    - DuckDB との互換性考慮（executemany に空リストを渡さない等）やテストしやすさのための id_token 注入を想定。
  - jquants_client のラッパーやエンドポイントへの接続／保存処理との連携を想定した設計。

- リサーチ（ファクター・特徴量） (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER/ROE）を DuckDB 上の SQL / Python 組合せで実装。
    - データ不足時の None 処理、結果を (date, code) キーの dict リストとして返却。
  - 特徴量探索ユーティリティ (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）：任意ホライズンの将来リターンを効率的に取得。
    - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関を実装（同順位の平均ランク処理含む）。
    - ランク変換（rank）と統計サマリー（factor_summary）を実装。
  - research パッケージの __all__ として主要関数を再エクスポート。

### 変更 (Changed)

- 設計方針上の明示
  - 主要な分析 / モデル生成関数はすべてルックアヘッド（datetime.today 等）を直接参照しない設計として実装。
  - DB 書き込みは冪等（上書き/DELETE→INSERT）で実装し、部分失敗時のデータ保護を考慮。

### 修正 (Fixed)

- （初回リリースにつき該当項目なし）

### 注意点 / 既知の制約 (Notes / Known limitations)

- OpenAI 連携
  - OpenAI API（gpt-4o-mini）利用箇所では API キーが必須。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定する必要がある。未設定時は ValueError を送出する仕様。
  - JSON Mode を利用するが、LLM の返却が不正な場合に備えてレスポンスパースの回復処理（外側の {} 抽出等）を行うよう実装している。
- フェイルセーフ
  - LLM 呼び出し失敗時はスコアを 0.0 にフォールバック（regime 判定）またはスキップ（news スコアリング）するなどフェイルセーフ設計。
- DuckDB 互換性
  - executemany に空リストを渡せないバージョンを考慮した分岐を実装しているが、環境によっては挙動差が発生する可能性あり。
- テスト用フック
  - _call_openai_api はテスト時に差し替え可能（unittest.mock で patch）。
- 実装上の不完全箇所（要注意）
  - pipeline.py の末尾付近に実装途上と思われる断片（例: return date.fro）が残っています。これは現在のソース切り出しでの欠落・タイポの可能性があるため、リリース前に修正・補完が必要です。

### 破壊的変更 (Breaking Changes)

- なし（初回リリース）

---

作者注: 本 CHANGELOG はリポジトリ内のソースコードから実装内容と設計意図を推測して作成したものです。実際のリリースノートとして利用する場合は、リリース時の日付・バージョン・未完了タスク（上記の pipeline の未完箇所など）を確認のうえ必要に応じて調整してください。