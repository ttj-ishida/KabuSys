# Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供します。

### 追加 (Added)

- パッケージ全体
  - kabusys パッケージ初版を追加。パッケージバージョンは `0.1.0`。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義（将来の拡張を想定）。

- 設定 / 環境管理 (`kabusys.config`)
  - .env/.env.local から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索（CWD 非依存）。
    - 環境変数の読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール等に対応。
  - protected（OS 環境変数）の概念を導入し、`.env.local` の上書き制御を安全に実施。
  - `Settings` クラスを公開:
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを提供（必須変数は未設定時に ValueError を送出）。
    - `env` / `log_level` の検証（許容値セットを定義）。
    - 環境判定ユーティリティ: `is_live`, `is_paper`, `is_dev`。

- AI（ニュース NLP / レジーム判定） (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp.score_news`)
    - 指定日のニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティを実装。
    - `raw_news` と `news_symbols` から銘柄ごとに記事を集約し、1銘柄あたり最大記事数・最大文字数でトリムして OpenAI（gpt-4o-mini）の JSON モードへバッチ送信。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、指数的バックオフを使ったリトライ（429/ネットワーク断/タイムアウト/5xx を対象）。
    - レスポンスのバリデーション（JSON 抽出、`results` 配列、既知コードのみ採用、スコアは数値かつ有限であること）を行い、スコアを ±1 にクリップ。
    - 書き込みはトランザクションで冪等（部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しは差し替え可能（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して、日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200 比率を計算（target_date 未満のみ使用しルックアヘッドを回避）。
    - raw_news からマクロキーワードでフィルタした記事タイトルを取得し、OpenAI（gpt-4o-mini）でマクロセンチメントを算出（記事がない場合は LLM 呼び出しをスキップ）。
    - OpenAI 呼び出しは再試行・エラーでフェイルセーフにより macro_sentiment=0.0 を採用。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。テスト時に差し替えやすい実装。

  - 共通設計方針（AI モジュール）
    - datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取ることでルックアヘッドバイアスを回避。
    - OpenAI レスポンスのパース失敗や API エラーは例外にしない（警告ログを出してフェイルセーフ処理を行う）。

- データ基盤 (`kabusys.data`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダー（祝日・半日取引・SQ）を扱うユーティリティを実装。
    - 営業日判定: `is_trading_day`, `is_sq_day`。
    - 隣接営業日検索: `next_trading_day`, `prev_trading_day`（最大探索日数を設定して無限ループを防止）。
    - 期間の営業日一覧取得: `get_trading_days`（DBにデータがある場合は DB 値優先、未登録日は曜日フォールバック）。
    - 夜間バッチ更新ジョブ: `calendar_update_job`（J-Quants クライアントを通じた差分フェッチ、バックフィル、健全性チェック）。
    - DB が未登録時の曜日ベースフォールバックや NULL 値検出時の警告ロジックを実装。
  - ETL / パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETLResult データクラスを定義（取得件数、保存件数、品質問題、エラーの集約）。
    - パイプライン設計:
      - 差分更新、バックフィル（デフォルト数日）、品質チェックフレームワークとの連携。
      - jquants_client による保存（Idempotent、ON CONFLICT を想定）。
      - DuckDB の互換性を考慮（executemany に空リストを渡さないなどの注意）。
    - `kabusys.data.etl` で ETLResult を再エクスポート。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum: 1M/3M/6M リターンの計算と 200 日移動平均乖離（ma200_dev）。データ不足時は None を返す。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比（volume_ratio）。
    - Value: PER（EPS がゼロ/欠損時は None）、ROE を raw_financials から取得して計算。
    - すべて DuckDB（prices_daily / raw_financials）に対する SQL 実行ベースで実装。実ポジション操作や外部 API 呼び出しは行わない設計。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算: `calc_forward_returns`（任意ホライズンのリードによる fwd_Xd を生成、horizons の検証あり）。
    - IC 計算（Spearman ランク相関）: `calc_ic`（欠損・同値等の処理を考慮）。
    - ランク変換ユーティリティ: `rank`（同順位は平均ランク、丸めで ties の扱いを安定化）。
    - 統計サマリー: `factor_summary`（count/mean/std/min/max/median）。
    - 余分な外部依存を避け、標準ライブラリと DuckDB のみで実装。

### 変更 (Changed)

- 初回リリースのため履歴はなし。

### 修正 (Fixed)

- 初回リリースのため修正履歴はなし。

### 注意事項 / 実装ノート (Notes)

- OpenAI の呼び出しは gpt-4o-mini を前提とし、JSON Mode（response_format を使用）でのやり取りを期待します。レスポンスの前後に余計なテキストが混入するケースを想定した復元ロジックを実装していますが、API の応答形式変更には注意が必要です。
- ルックアヘッドバイアス回避のため、AI モジュールやリサーチモジュールはすべて明示的な target_date を受け取り、内部で date.today()/datetime.now() を参照しません。
- DuckDB のバージョン互換性に関して幾つかの実装上の注意（executemany に空リストを渡さない等）を盛り込んでいます。
- 環境変数の自動読み込みはプロジェクトルート検出に依存するため、配布後の動作を考慮して `KABUSYS_DISABLE_AUTO_ENV_LOAD` により抑止可能です。
- jquants_client（データ取得・保存）や外部実装は参照していますが、本変更ログのソース一覧には含まれていません（別モジュールとして提供される想定）。

--- 

今後のリリースでは、strategy / execution / monitoring の具体的な戦略実装、実取引インテグレーション、モニタリング・アラート機能の追加を予定しています。