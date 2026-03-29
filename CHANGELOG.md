# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリース日付はコードベースの内容に基づいて推定しています。

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。
主にデータ取得・カレンダー管理・リサーチ（ファクター計算）・AI ベースのニュース解析と
市場レジーム判定を含みます。DuckDB をデータストアとして想定した実装です。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - 公開モジュール: data, strategy, execution, monitoring（__all__ に定義）

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび OS 環境変数の読み込み（自動ロード機構）
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD 非依存）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動ロードを無効にするためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env パーサーの実装（クォート、エスケープ、コメント処理、`export KEY=val` 対応）
  - 上書き制御（override / protected）をサポート
  - 必須環境変数取得ヘルパー `_require` と、Settings クラスを実装
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供
    - `env` / `log_level` の値検証（許容値セット）および `is_live` / `is_paper` / `is_dev` の便宜プロパティ
    - デフォルト値（例: KABUSYS_API_BASE_URL, DUCKDB_PATH 等）のサポート

- AI ニュース解析 (`kabusys.ai.news_nlp`)
  - ニュースのタイムウィンドウ計算: `calc_news_window(target_date)`（JST→UTC の変換考慮）
  - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）にバッチで投げる処理: `score_news(conn, target_date, api_key=None)`
    - バッチサイズ、記事数・文字数トリム制約、JSON Mode を用いた厳密なレスポンス検証
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）
    - レスポンス検証ロジック（`_validate_and_extract`）により不正レスポンスはスキップし例外を投げないフェイルセーフ
    - DuckDB への書き込みは冪等性を意識（対象コードのみ DELETE→INSERT）し、部分失敗時に既存データを保護
    - 書き込み前の空パラメータ回避（DuckDB 互換性対応）

- AI 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225連動型）を用いた 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定: `score_regime(conn, target_date, api_key=None)`
    - MA200 の乖離 `_calc_ma200_ratio`（ルックアヘッド防止のため target_date 未満のデータのみを使用）
    - マクロキーワードでニュースを抽出する `_fetch_macro_news`
    - OpenAI 呼び出し（独自実装）とマクロスコア算出 `_score_macro`（リトライ・フォールバック）
    - MA と マクロ重み付け（70% / 30%）、スコアクリップ、閾値によるラベリング（bull/neutral/bear）
    - 結果の DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）

- データ・カレンダー管理 (`kabusys.data.calendar_management`)
  - マーケットカレンダーの照会／判定 API
    - 営業日判定: `is_trading_day(conn, d)`
    - SQ 判定: `is_sq_day(conn, d)`
    - 翌営業日／前営業日: `next_trading_day(conn, d)`, `prev_trading_day(conn, d)`
    - 期間内営業日取得: `get_trading_days(conn, start, end)`
  - カレンダーデータの夜間差分更新ジョブ: `calendar_update_job(conn, lookahead_days=90)`
    - J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存を実施
  - カレンダーデータが未取得の場合の曜日ベースのフォールバック実装（土日を非営業日扱い）
  - 最大探索日数上限（無限ループ防止）や NULL 発見時の警告ログ等を実装

- ETL / パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETL 実装方針に基づくユーティリティを実装
  - ETL 実行結果を表すデータクラス `ETLResult`（target_date, fetched/saved counts, quality_issues, errors 等）
    - `has_errors` / `has_quality_errors` / `to_dict`（quality issue のシリアライズ）を実装
  - 差分取得用のユーティリティ（テーブル存在確認、最大日付取得等）
  - `kabusys.data.etl` で `ETLResult` を再エクスポート

- リサーチ（ファクター計算） (`kabusys.research`)
  - ファクター計算群: `calc_momentum`, `calc_value`, `calc_volatility`
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（欠損時は None）
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - Value: PER（EPS が 0/欠損の場合は None）、ROE（直近報告値）
  - 特徴量探索ユーティリティ: `calc_forward_returns`, `calc_ic`, `rank`, `factor_summary`
    - 将来リターン計算（任意ホライズン、入力検証、単一クエリで効率的に取得）
    - IC（Spearman）の実装（ランク付け、同順位は平均ランク処理）
    - 統計サマリー（count/mean/std/min/max/median）
  - Z スコア正規化等の補助は `kabusys.data.stats` を介して利用

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### 既知の設計上の注意点（ドキュメント的補足）
- ルックアヘッドバイアス対策:
  - AI / ファクター / リサーチ系関数は内で datetime.today() や date.today() を参照せず、必ず引数の target_date を使う設計。
  - prices_daily 等のクエリでは target_date 未満または指定範囲のみを参照。
- フェイルセーフ:
  - OpenAI API の失敗や JSON パースエラーは多くの箇所で 0.0 や空スコアにフォールバックし、処理全体を継続する実装。
- DuckDB 互換性:
  - executemany の空リスト問題や list バインドの互換性に配慮した実装（個別 DELETE を使う等）。
- 冪等性:
  - DB 書き込みは基本的に冪等（DELETE→INSERT、ON CONFLICT 想定）を意識している。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（例: _call_openai_api）は差し替え（mock）可能な形で定義。

---

今後の想定作業（例）
- strategy / execution / monitoring 周りの具体実装（発注ロジック、監視・アラート）
- 単体テスト・統合テストの追加（モックによる外部 API の検証）
- ドキュメント（API 仕様・運用手順）の整備
- エラーメトリクス・監視の拡充

--- 

（注）本 CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、機能ごとにより詳細な変更点（関数単位の実装差分や既知のバグ）を追加します。