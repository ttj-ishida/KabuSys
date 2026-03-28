Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

0.1.0 - 2026-03-28
------------------

初回公開リリース。

Added
- パッケージ基盤
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"。
  - パッケージ公開インターフェースを整理（__all__ に data, strategy, execution, monitoring を定義）。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースは以下をサポート・堅牢化:
    - export KEY=val 形式への対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント処理（クォート有無に応じた扱い）。
  - 上書き制御（override）と保護キー（protected）による OS 環境変数保護を実装。
  - Settings クラスを提供してアプリ設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / データベースパス等の設定をプロパティ化。
    - env と log_level の値検証（許容値以外は ValueError）。
    - is_live / is_paper / is_dev のヘルパーを提供。

- AI 関連 (src/kabusys/ai)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini, JSON Mode) へバッチ送信してセンチメントを取得。
    - time window 計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window に実装。
    - 1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチサイズ制御（_BATCH_SIZE = 20）、チャンク毎に API 呼び出し。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ（最大回数指定）。
    - レスポンスのバリデーションと数値クリッピング（±1.0）。不正応答はスキップして継続。
    - 書き込みは部分失敗を考慮し、取得できたコードのみ DELETE → INSERT の置換方式で ai_scores に保存。
    - テスト用に OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch で置換）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - 日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
    - マクロニュースの抽出（マクロキーワード群）→ LLM（gpt-4o-mini）評価 → スコア合成（クリップ）→ market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ設計。
    - OpenAI 呼び出しは専用関数で実装し、モジュール間で private 関数を共有しない設計。

- Data / ETL / カレンダー (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間バッチ更新処理（calendar_update_job）を実装。
    - market_calendar を参照する営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない/未登録日の場合は曜日ベースのフォールバック（土日非営業日）。
    - 最大探索範囲の制限や健全性チェック、バックフィルロジックを備える。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分取得→保存（jquants_client の save_* を利用して idempotent 保存）→品質チェック（quality モジュール）という処理方針に基づく実装。
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラーサマリ含む）。
    - DuckDB の互換性考慮（テーブル未存在時の扱い、executemany 空リスト制約など）を考慮した実装。
    - データ取得の backfill デフォルトやカレンダー先読みロジックを備える。

- Research / ファクター類 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: mom_1m / mom_3m / mom_6m、200日移動平均乖離 ma200_dev。
    - Volatility / Liquidity: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - Value: PER（EPS が非ゼロの場合）、ROE（raw_financials から取得）。
    - DuckDB 内で SQL を主体に効率的に計算し、データ不足時は None を返す安全設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（任意 horizon のサポート、入力検証）。
    - IC（Information Coefficient）計算（スピアマンのランク相関） calc_ic。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めにより ties の扱いを安定化）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。

Changed
- 初回リリースのため、既存の API 設計や動作仕様をソース上に明記（Look-ahead バイアス防止等の設計方針をコードコメントに記載）。

Fixed
- （初期リリース）実装上の堅牢化として以下を実装・考慮:
  - OpenAI レスポンスパース失敗や API エラー時に例外を上位に伝播させずフェイルセーフで継続する箇所多数（ニューススコア・レジーム判定等）。
  - DuckDB executemany の空リスト問題への対応（空時は呼び出さない）。

Notes / 実装上の重要な設計判断
- 全体を通して「ルックアヘッドバイアスを避ける」設計を優先:
  - datetime.today() / date.today() を内部ロジックで無差別に参照しない（外部から target_date を注入する設計）。
  - DB クエリは target_date 未満／<= 等の条件で未来データ参照を防止。
- 外部 API（OpenAI / J-Quants）呼び出しはリトライ・バックオフ・フェイルセーフを備え、部分失敗時に他データを破壊しない（部分置換やコード絞り込み等）。
- テスト容易性を考慮して、OpenAI 呼び出し点は patch による差し替えが可能な実装になっている。
- DuckDB 依存の実装は互換性を考慮しつつ SQL ウィンドウ関数等を活用して高効率に計算する。

Security
- OpenAI API キー未設定時は明示的に ValueError を発生させる（誤った沈黙挙動を避ける）。
- 環境変数の自動ロードは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

今後の予定（想定）
- strategy / execution / monitoring の具象実装と統合テスト。
- テストカバレッジ強化、CI 実行例の追加。
- J-Quants / kabu API 周りの追加ユーティリティ拡充。
- ドキュメント（Usage / Deployment / Examples）の整備。

---