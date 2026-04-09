# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。

## [0.1.0] - 2026-04-09

初回リリース — 日本株自動売買システム「KabuSys」最初の公開バージョン。

### 追加 (Added)
- パッケージ基盤
  - `kabusys` パッケージを追加。パッケージメタ情報として `__version__ = "0.1.0"` を設定。
  - パブリック API: `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義。

- 設定 / 環境変数管理 (`kabusys.config`)
  - プロジェクトルート検出機能：`.git` または `pyproject.toml` を基準に自動でルートを探索（CWD に依存しない）。
  - `.env` / `.env.local` 自動ロード機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で利用）。
  - `.env` パーサーを実装：
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート対応（バックスラッシュによるエスケープ処理を考慮）。
    - インラインコメントの扱い（クォート内は無視、非クォートはスペース直前の `#` をコメント判定）。
  - 環境変数保護機能：OS 環境変数を `protected` として `.env.local` の上書きから保護。
  - `Settings` クラスを提供し、環境変数をプロパティとして型変換・検証して取得:
    - J-Quants / kabuステーション / LINE / DB / 監視関連など多数の設定プロパティ。
    - バリデーション例: `PAPER_FILL_MODE`（有効値: `"instant"|"partial"|"never"|"reject"`）、`KABUSYS_ENV`（`development|paper_trading|live`）、`LOG_LEVEL`（`DEBUG|INFO|...`）等。
    - Path を返す設定は `Path.expanduser()` により `~` を解釈。

- AI（ニュースNLP・レジーム判定）
  - `kabusys.ai.news_nlp`:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントをスコアリングする `score_news` を実装。
    - タイムウィンドウ（JST 前日15:00 ～ 当日08:30）計算ユーティリティ `calc_news_window` を提供（UTC 変換済み）。
    - バッチ送信（チャンクサイズ最大 20 銘柄）、1銘柄あたり記事数・文字数制限（上限: 10 件、3000 文字）を実装。
    - OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON レスポンスを期待。パース失敗に備えた復元ロジックを備える。
    - リトライ処理（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンス検証: `results` 配列存在、各要素に `code` と `score`、未知コードの無視、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは部分失敗を避けるため対象コードのみ DELETE → INSERT の冪等更新を実施（`BEGIN`/`COMMIT`/`ROLLBACK` 保護）。
    - APIキー注入: `api_key` 引数 or 環境変数 `OPENAI_API_KEY`。
  - `kabusys.ai.regime_detector`:
    - ETF 1321 の直近 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム (`bull|neutral|bear`) を判定する `score_regime` を実装。
    - MA200 乖離（最新終値 / MA200）にスケール・重み付け（MA 70%、マクロ 30%）を行いスコアを合成。閾値によりラベル決定。
    - マクロニュースはキーワードでフィルタ（複数キーワード）、最大 20 記事を LLM に渡す。
    - OpenAI 呼び出しに対するリトライ・エラーハンドリングを実装（フェイルセーフ時は macro_sentiment=0.0）。
    - 結果は `market_regime` テーブルへ冪等書き込み（DELETE → INSERT、トランザクション管理）。

- データ (Data platform)
  - `kabusys.data.calendar_management`:
    - JPX マーケットカレンダー管理、営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合の曜日ベースフォールバック（週末: 非営業日）。
    - 最大探索日数 `_MAX_SEARCH_DAYS` により無限ループを防止。
    - 夜間更新ジョブ `calendar_update_job` を実装。J-Quants クライアントを使い差分取得 → 保存（バックフィル、健全性チェックを含む）。
  - `kabusys.data.pipeline`, `kabusys.data.etl`:
    - ETL パイプライン用の構造と方針を実装（差分更新、品質チェック、idempotent 保存）。
    - `ETLResult` データクラスを提供（`target_date`, 各種 fetched/saved カウント, `quality_issues`, `errors`、ユーティリティプロパティ `has_errors`, `has_quality_errors`, `to_dict`）。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- リサーチ（ファクター計算・特徴量探索）
  - `kabusys.research.factor_research`:
    - `calc_momentum`: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）。
    - `calc_volatility`: 20日 ATR（平均）、相対 ATR（ATR/close）、20日平均売買代金、出来高比率を計算。
    - `calc_value`: raw_financials から最新財務データを取得し PER/ROE を計算（EPS=0 の場合 PER は None）。
    - DuckDB を用いた SQL ウィンドウ関数中心の実装。
  - `kabusys.research.feature_exploration`:
    - `calc_forward_returns`: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを取得。horizons の入力検証あり。
    - `calc_ic`: スピアマンランク相関（IC）を実装。欠損・定数分散・サンプル数不足時は None を返す。
    - `rank`: 同順位は平均ランクとするランク付け（丸めで ties 判定の安定化）。
    - `factor_summary`: 各ファクター列の count/mean/std/min/max/median を計算。

- その他
  - DuckDB 互換性への考慮:
    - `executemany` に空リストを渡さないガードを追加（DuckDB 0.10 の制約回避）。
    - 日付値の変換ユーティリティ（DuckDB の返り値を date に変換）。
  - ロギング/フェイルセーフ:
    - 多くの箇所で詳細なログ（info/debug/warning/exception）を追加し、API 失敗時は例外を投げずにフォールバックまたはスキップする設計。
    - DB 書き込み時のトランザクション管理・ROLLBACK の失敗ログを追加。

### 変更 (Changed)
- 初回リリースのため該当項目なし。

### 修正 (Fixed)
- 初回リリースのため該当項目なし。

### 削除 (Removed)
- 初回リリースのため該当項目なし。

### セキュリティ (Security)
- 初回リリースのため該当項目なし。

---

注記:
- 設計方針として「datetime.today()/date.today() をスコープ内部で直接参照しない」ことでルックアヘッドバイアスを防止しています（対象日は関数引数で与える設計）。
- OpenAI 呼び出しは SDK（openai.OpenAI）を利用。テスト容易性のため内部 API 呼び出し関数に対してモック差し替えを想定しています（unittest.mock.patch を利用可能）。
- 外部に依存する主要コンポーネント: DuckDB、OpenAI SDK、J-Quants クライアント（`kabusys.data.jquants_client`）。
- 今後のリリースでは、strategy / execution / monitoring モジュールの実装・改善、テスト増強、パフォーマンス最適化、エラーハンドリングの拡張などを予定しています。