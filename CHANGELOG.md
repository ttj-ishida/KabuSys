# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に従って管理しています。

現在のバージョン: 0.1.0 — 2026-03-29

## [0.1.0] - 2026-03-29

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化。バージョン情報 `__version__ = "0.1.0"` と公開モジュール `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義。

- 環境設定・ロード機能 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み:
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して検出（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - .env パーサの強化:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理、クォート無しのコメント判定などを適切に処理。
    - ファイル読み込み失敗時に警告を出力。
  - 必須設定取得ヘルパー `_require` と、各種プロパティ:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/環境（development/paper_trading/live）/ログレベル検証など。
    - `is_live`, `is_paper`, `is_dev` のブール切替。

- ニュースNLP（AI）モジュール (`kabusys.ai.news_nlp`)
  - score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードを用いて銘柄単位のセンチメント（-1.0〜1.0）を算出。
    - 1銘柄あたりの記事上限・文字上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を設定してトークン爆発を回避。
    - 最大20銘柄ずつのバッチ送信（_BATCH_SIZE）。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの厳密バリデーション（JSON 抽出、results キー、型チェック、既知コードのみ採用、数値性検査）。
    - DuckDB 互換性を考慮した書き込み処理（部分書込み保護、executemany の空リスト回避）。
    - 失敗時は安全にスキップし、フェイルセーフを確保（例外を上位へ投げない設計）。

  - calc_news_window(target_date)
    - JST 基準のニュース収集ウィンドウ生成（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。

  - 内部ユーティリティ:
    - OpenAI 呼び出しラッパー（テスト時に差し替え可能）。
    - レスポンス検証ロジックとスコアクリッピング。

- 市場レジーム判定モジュール (`kabusys.ai.regime_detector`)
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次の市場レジーム（bull / neutral / bear）を判定し `market_regime` テーブルへ冪等書き込み。
    - ma200 の計算でルックアヘッドバイアスを防ぐ（target_date 未満のデータのみ利用）。
    - マクロニュース取得は news_nlp.calc_news_window を利用し、OpenAI（gpt-4o-mini）で JSON スコアを取得。
    - API 失敗時は macro_sentiment = 0.0 へフォールバックするフェイルセーフ。
    - 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン。失敗時は ROLLBACK を試行。

- リサーチ（ファクター計算）モジュール (`kabusys.research`)
  - factor_research:
    - calc_momentum(conn, target_date)
      - 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility(conn, target_date)
      - 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。欠損は None。
    - calc_value(conn, target_date)
      - raw_financials と株価を結合して PER/ROE を計算（EPS が 0/欠損の時は None）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None)
      - 指定ホライズン先の将来リターンをまとめて取得。horizons のバリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンランク相関（IC）を計算（有効レコード不足時は None）。
    - rank(values) / factor_summary(records, columns)
      - 同順位は平均ランク、基本統計量（count/mean/std/min/max/median）を算出。
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリと DuckDB SQL を併用する設計。すべての関数は lookahead バイアスに配慮（内部で datetime.today() を参照しない）。

- データプラットフォーム関連 (`kabusys.data`)
  - calendar_management:
    - 市場カレンダー操作ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar の存在チェック、曜日ベースのフォールバック、最大探索日数制限、バックフィルロジック、calendar_update_job による J-Quants からの差分取得と冪等保存を実装。
    - 異常（極端に将来の日付など）時の健全性チェックとログ出力。
  - pipeline / etl:
    - ETLResult データクラスの公開（kabusys.data.etl で再エクスポート）。
    - ETLResult は取得件数／保存件数／品質問題（quality_issues）／エラーリスト等を含み、has_errors / has_quality_errors / to_dict を提供。
    - ETL の設計方針として差分更新、backfill、品質チェックの集約（Fail-Fast ではない）を採用。
  - DuckDB に対する互換性考慮（情報スキーマの利用、executemany の空リスト回避、日付型変換ユーティリティ等）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーを引数で注入可能（テスト容易化）かつ環境変数 `OPENAI_API_KEY` にフォールバックする設計。
- 重大なセキュリティ問題は本バージョンでは報告なし。ただし API キー管理・ネットワーク通信は運用者で適切に管理してください。

### 注意事項 / 実装上の設計判断（重要）
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・リサーチ関数はいずれも内部で datetime.today()/date.today() を参照せず、必ず呼び出し元から `target_date` を受け取る設計。
- フェイルセーフ:
  - OpenAI 呼び出し失敗時は例外で処理を中断せず、スコアを 0.0 にフォールバックしたり該当チャンクをスキップすることで全体の ETL / バッチ処理が継続するようにしている。
- DuckDB 互換性:
  - DuckDB のバージョン差異（executemany の空リスト禁止やリスト型バインドの不安定性）を考慮した実装がなされている。
- テスト容易性:
  - OpenAI 呼び出しラッパーを内部関数として分離しており、unittest.mock.patch により差し替えが可能。

---

今後のリリースでは、戦略実行（strategy / execution）とモニタリング周りの具体的な実装・CLI/ジョブ制御・監視通知等を追加していく予定です。