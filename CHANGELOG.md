# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従って管理されています。

なお、以下は与えられたコードベースから推測してまとめた変更点（機能説明）です。

## [0.1.0] - Initial release
最初のリリース。主要な機能群（設定管理、データ ETL / カレンダー管理、リサーチ用ファクター計算、AI を用いたニュース・レジーム判定など）を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ version を `0.1.0` として公開（src/kabusys/__init__.py）。
  - パッケージの公開モジュール一覧を定義: data, strategy, execution, monitoring。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - .env パーサー: コメント行、`export KEY=val` 形式、クォートされた値とバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - 上書き制御: override / protected キーをサポートし、OS 環境変数を保護して .env による上書きを防止。
  - Settings クラスを提供し、型付きプロパティ経由で設定値を取得:
    - J-Quants / kabuAPI / Slack / DB パス（DuckDB / SQLite）等の設定を取得するプロパティを実装。
    - `KABUSYS_ENV`（development/paper_trading/live）および `LOG_LEVEL` の値検証を行う。
    - is_live / is_paper / is_dev のユーティリティを提供。
  - 必須環境変数未設定時は ValueError を送出する `_require` 実装。

- AI モジュール（src/kabusys/ai/）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントを算出。
    - 出力は JSON Mode を想定。レスポンスバリデーション（results 配列、code, score の検証）を実装。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、トークン肥大化対策（最大記事数・最大文字数トリム）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ。
    - スコアは ±1.0 にクリップ。部分的失敗時にも既存スコアを保護するため、書き込みは対象コードに限定した DELETE → INSERT の冪等操作で実行。
    - API キー解決: 関数引数または環境変数 `OPENAI_API_KEY`。
    - ルックアヘッドバイアス防止: 日時の決定は引数 `target_date` ベースで行い、 date.today() を使用しない設計。
    - 公開 API: `score_news(conn, target_date, api_key=None)`（書き込み件数を返す）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し `market_regime` テーブルへ書き込み。
    - マクロニュースの抽出はキーワードベース（複数の日本・米国キーワードを列挙）。
    - OpenAI 呼び出しは JSON Mode を使用し、リトライ・フォールバック戦略（API 失敗時は macro_sentiment=0.0）を実装。
    - スコア合成・閾値判定（BULL_THRESHOLD/BEAR_THRESHOLD）と冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。例外時は ROLLBACK を試みる。
    - 公開 API: `score_regime(conn, target_date, api_key=None)`（成功時に 1 を返す）。
  - 共通設計
    - OpenAI 呼び出しラッパー関数は各モジュール内で独立実装（モジュール間の内部関数共有を避ける）。

- データ処理（src/kabusys/data/）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがある場合は DB 値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 最大探索日数の上限・健全性チェック（将来日付の異常検出）を実装。
    - 夜間バッチジョブ `calendar_update_job(conn, lookahead_days=...)`：J-Quants API から差分取得し `market_calendar` を冪等的に保存。バックフィル日数を設定して後出し修正を吸収する。
    - J-Quants クライアントへの依存を抽象化（kabusys.data.jquants_client を使用）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を実装（target_date, fetched/saved counts, quality_issues, errors 等を保持）。
    - ETL の差分取得・保存・品質チェックの設計に基づくユーティリティ群（関数群は pipeline モジュールで実装予定／記載）。
    - `ETLResult.to_dict()` により品質問題を辞書化して出力可能。
    - etl モジュールでは pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m, ma200_dev を計算する `calc_momentum(conn, target_date)`。
    - Volatility & Liquidity: 20日 ATR（atr_20）および相対 ATR (atr_pct), avg_turnover, volume_ratio を計算する `calc_volatility(conn, target_date)`。
    - Value: PER（価格 / EPS）および ROE を raw_financials と prices_daily 組合せで計算する `calc_value(conn, target_date)`。EPS が 0 または欠損時は None を返す。
    - 各関数はデータ不足時に None を返す挙動で安全に動作。DuckDB を用いたウィンドウ関数利用で高速集計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算 `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman の順位相関を算出。3 件未満で None を返す）。
    - ランク化ユーティリティ `rank(values)`（同順位は平均ランクで処理、丸めによる ties 対応）。
    - 統計サマリー `factor_summary(records, columns)`（count/mean/std/min/max/median を算出）。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 廃止 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。
- 注意: OpenAI API キーや外部トークンは環境変数で管理する設計（必須設定時は例外を送出）。.env 自動ロード機能はテスト等で無効化可能。

---

補足メモ（設計方針）
- ルックアヘッドバイアス回避: AI / スコアリング処理は常に引数の target_date を基準に、DB クエリは target_date より前のデータのみを参照するよう設計されています。
- フェイルセーフ: API 呼び出し失敗時は例外で停止させずフォールバック値（例: macro_sentiment=0.0）を使用する箇所があるため、バッチ処理の継続性を重視しています。
- 冪等性: DB への書き込みは DELETE → INSERT や ON CONFLICT など冪等化を意識して実装されています。
- DuckDB をデータ処理の中心に利用する設計で、executemany の空パラメータ回避など DuckDB の実装の癖にも対応しています。

この CHANGELOG はコードから推測して作成したものであり、実際のリリースノートはリリース時の意図や変更履歴に合わせて調整してください。