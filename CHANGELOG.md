Keep a Changelog
すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

0.1.0 - 2026-03-31
-----------------
Added
- パッケージ基本
  - 初期リリース。パッケージ名: kabusys。パッケージ公開用 __version__ を 0.1.0 に設定。
  - パッケージ外部公開モジュール: data, research, ai, execution, monitoring, strategy（__all__ に準備）。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを停止可能。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント条件を考慮）。
  - override / protected オプションにより OS 環境変数の保護や .env.local による上書きをサポート。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / システム環境などのプロパティ経由で取得可能。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）と必須値取得時のエラー通知 (_require)。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数上限（記事数 10 件 / 銘柄、最大文字数 3000）によるトリム実装。
    - 再試行ポリシー（429・ネットワーク断・タイムアウト・5xx の指数バックオフ）、レスポンスの厳密なバリデーション（JSON 抽出、results の検査、未知コード無視、数値チェック）。
    - フェイルセーフ: API 失敗やバリデーション失敗は例外を投げず該当チャンク/銘柄をスキップ。
    - DuckDB への書き込みは部分的置換（DELETE → INSERT）で idempotent に実行。DuckDB executemany の空リスト制約に対応。
    - テスト容易性: _call_openai_api を patch で差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。
    - calc_news_window(target_date) により JST ベースのニュース取得ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC naive datetime で計算。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime を日次判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、データ不足時のフォールバック（1.0）やログ出力を行う（ルックアヘッドバイアス防止）。
    - マクロニュースは raw_news からマクロキーワード（日本・米国系を含む）で抽出し、最大 20 件を LLM に投入。
    - OpenAI 呼び出しは専用関数で実装し、リトライ・バックオフ・5xx 判定・パース失敗時は macro_sentiment=0.0 にフォールバック（例外を上げない）。
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。例外時は ROLLBACK を試行。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日 MA 乖離）を DuckDB クエリで計算。データ不足時は None。
    - Volatility: 20日 ATR（true_range の NULL 伝播制御）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - Value: raw_financials から報告日ベースの最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API へ依存しない。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：指定 horizon（デフォルト [1,5,21]）に対するリターンを LEAD を使って一括取得。
    - IC（Information Coefficient）計算（calc_ic）：factor と将来リターンを code で結合し、スピアマン ρ を算出。データ不十分時は None。
    - ランク変換（rank）：同順位は平均ランクで処理、丸め誤差対策で round(v, 12) を使用。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research/__init__.py で主要関数を再エクスポート（zscore_normalize は data.stats から参照）。

- データプラットフォーム / ETL / カレンダー (src/kabusys/data/)
  - calendar_management.py
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得し market_calendar を idempotent に保存。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB データ優先、未登録日は曜日ベースのフォールバック。
    - 最大探索日数やバックフィル、健全性チェック（未来日数閾値）を組み込み、無限ループの回避や API 側の修正取り込みを考慮。
  - pipeline.py / etl.py
    - ETLResult dataclass を実装（ETL の各種取得/保存件数、品質問題、エラーの集約）。
    - ETL パイプラインの設計（差分更新、save_* の idempotent 呼び出し、品質チェックの収集方針）を反映したユーティリティ基盤を実装。
    - jquants_client と quality モジュールを利用することで外部 API 連携と品質検査を組み合わせる想定。
  - data パッケージは ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- インフラ設計・品質/テスト配慮
  - すべての時刻処理で datetime.today()/date.today() の直接参照を避け、関数引数で日付を受け取る設計（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出し箇所はテストで差し替え可能（_call_openai_api を patch しやすく設計）。
  - API 呼び出しのリトライ/バックオフ、5xx と非 5xx の扱い分離、レスポンスパース失敗時のフォールバック動作を徹底。
  - DuckDB のバージョン差異を考慮した実装（executemany の空リスト禁止回避、リストバインドの注意点等）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated / Removed / Security
- なし。

Notes / 実装上の注意
- OpenAI の API キーは api_key 引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY も参照。
- .env パーサは一般的なシェルの取り扱いに近い挙動（export/quote/コメント）を目指しているが、すべての corner case を網羅するわけではない。
- DuckDB を前提とした SQL 実装のため、他の DB では動作しない箇所がある可能性がある（特に window 関数・executemany の挙動）。

今後の予定（例）
- score_news / score_regime のテストカバレッジ拡充（外部 API モックを使ったユニットテスト）。
- ETL 実行の CLI / スケジューラ統合、監視・通知機能の実装強化。
- research モジュールの追加指標や PBR・配当利回りなどの拡張。

--- 

（初回リリース用の CHANGELOG）