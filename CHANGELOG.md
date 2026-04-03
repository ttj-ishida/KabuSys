# Changelog

すべての重要な変更はこのファイルに記録されます。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。主要な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージメタ情報
  - pakage version: `kabusys.__version__ = "0.1.0"`
  - 公開モジュール: `__all__ = ["data", "strategy", "execution", "monitoring"]`（パッケージ構成の意図を明示）

- 環境設定管理 (`kabusys.config`)
  - .env ファイル / 環境変数の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env パーサーの強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無での差別化）
  - 既存 OS 環境変数を保護する `protected` 機構（.env 上書きを制御）
  - 必須環境変数取得ユーティリティ `_require()`（未設定時は ValueError）
  - Settings クラスを公開（J-Quants / kabu ステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供）
    - 環境値検証（`KABUSYS_ENV`, `LOG_LEVEL` の許容値チェック）
    - パスは `Path(...).expanduser()` を返却
    - 監視用しきい値（CPU/MEM/DISK）や kill フラグ設定等の取得

- AI モジュール（自然言語処理・市場レジーム判定）
  - `kabusys.ai.news_nlp`
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出
    - タイムウィンドウ（JST 前日15:00～当日08:30 に相当する UTC 範囲）を厳密に計算するユーティリティ `calc_news_window`
    - API 呼び出しのバッチ処理（最大 _BATCH_SIZE=20 銘柄/呼び出し）、記事トリム（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフ）
    - レスポンスの堅牢なバリデーション（JSON 抽出、results の検証、未知コードを無視、数値チェック、±1.0 にクリップ）
    - DuckDB への冪等的書き込み（DELETE → INSERT、トランザクション/ROLLBACK 対応）
    - テスト容易性: `_call_openai_api` の差し替えが可能
  - `kabusys.ai.regime_detector`
    - ETF 1321（日経225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - LLM は gpt-4o-mini を使用（JSON モード）、マクロキーワードでニュースをフィルタ
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 として継続
    - スコア合成・クリップ・閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）
    - `market_regime` テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK）
    - ルックアヘッドバイアス対策: date 比較は常に target_date 未満/以前の排他条件を使用し、datetime.today() を参照しない設計

- リサーチ（ファクター計算・特徴量探索）
  - `kabusys.research.factor_research`
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA 乖離）を計算する `calc_momentum`
    - ボラティリティ / 流動性: 20 日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio を計算する `calc_volatility`
    - バリュー: PER / ROE を計算する `calc_value`（raw_financials から最新レコードを取得）
    - 設計方針: DuckDB 上で SQL + Python による計算、外部 API にはアクセスしない
  - `kabusys.research.feature_exploration`
    - 将来リターン計算: `calc_forward_returns`（任意 horizon リスト、入力検証あり）
    - IC（Information Coefficient）計算: `calc_ic`（スピアマンρ、レコード結合とランク処理）
    - ランク関数 `rank`（同順位は平均ランクを返す実装）
    - 統計サマリー: `factor_summary`（count/mean/std/min/max/median）
    - 外部依存を持たない実装（pandas 等に依存しない）

- データ (Data Platform)
  - `kabusys.data.calendar_management`
    - JPX カレンダーの管理機能（market_calendar テーブル読み書き）と営業日判定ユーティリティ
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない/未登録日の場合は曜日ベース（平日を営業日）でフォールバックする一貫した動作
    - 最大探索範囲 `_MAX_SEARCH_DAYS` による無限ループ防止
    - 夜間バッチ `calendar_update_job`:
      - jquants_client 経由で差分取得・保存（バックフィルを含む）
      - 健全性チェック（過度に未来の日付が登録されている場合はスキップ）
  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプラインの骨格と `ETLResult` データクラスを公開
      - ETLResult は取得・保存数、品質チェック結果、エラー一覧などを保持し `to_dict()` を提供
    - 差分更新・バックフィル・品質チェックの設計方針を明示
    - jquants_client / quality モジュールとの連携用のユーティリティを実装

- パッケージ初期化・エクスポート
  - `kabusys.ai.__init__` で `score_news` を公開
  - `kabusys.research.__init__` で主要な分析ユーティリティを再エクスポート

### 修正 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 設計上の注記 / 制限事項 (Notes)
- ルックアヘッドバイアス回避のため、日付基準処理はすべて外部から与えられる `target_date` に依存し、内部で `datetime.today()` / `date.today()` を直接参照する実装は避けています（一部バッチは今日を基準にするが、分析関数は target_date ベース）。
- AI モジュールは OpenAI API（gpt-4o-mini）を使用する前提。API キーは引数で注入可能（`api_key`）か環境変数 `OPENAI_API_KEY` を参照します。未設定時は ValueError を送出。
- DuckDB への書き込みは冪等性（DELETE→INSERT、トランザクション）を意識しているため、部分失敗時にも既存データを不必要に消さない設計を採用しています。
- 一部のテーブル / クライアント（例: `jquants_client`）は別モジュールに分離されており、本リリースではインターフェース呼び出しを行います（実環境との接続設定が必要）。
- リサーチコードは外部ネットワークに依存せず、duckdb のみにアクセスする前提で設計されています（本番発注 API にはアクセスしない）。

---

今後のリリースでは、strategy / execution / monitoring の実装、テストカバレッジ強化、ドキュメント整備（使用例・DB スキーマ）などを予定しています。