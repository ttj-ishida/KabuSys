# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記録します。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した初期の変更履歴です。

フォーマット:
- Unreleased: 現在進行中の変更（未リリース）
- 各リリースは [バージョン] - YYYY-MM-DD の形式

---

## [Unreleased]

- なし（初回リリース直後のため未リリースの変更はありません）
- 注意事項 / 今後対応予定:
  - data.pipeline._get_max_date の実装末端が途中で切れており（`return date.fro` のような途中表現）、修正が必要。
  - いくつかのモジュール（例: execution, monitoring）が __init__ で公開されているが、ここに提示されたコードには詳細実装が含まれていません。関連する実装・テストの追加予定。

---

## [0.1.0] - 2026-03-31

初期公開リリース。日本株自動売買プラットフォームのコアユーティリティ群を提供します。

### Added
- パッケージ基礎
  - パッケージバージョンと公開 API を定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - モジュール群を __all__ で公開（data, strategy, execution, monitoring）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルや環境変数からの設定自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - プロジェクトルート検出は __file__ を起点に .git / pyproject.toml を探索（CWD 非依存）。
    - .env パーサは export 構文、クォートのエスケープ、インラインコメントの扱いに対応。
    - 環境変数上書き時に OS 環境変数を保護する protected セット機構を採用。
  - Settings クラスを提供し、アプリケーションで必要なキーをプロパティとして取得:
    - J-Quants, kabuステーション, Slack, DB パス（DuckDB/SQLite）, 監視閾値, 環境（development, paper_trading, live）やログレベルの検証など。
    - 必須変数未設定時は ValueError を送出する _require を実装。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を算出。
  - 機能:
    - JST ベースのニュースウィンドウ計算（前日 15:00 ～ 当日 08:30 JST を UTC に変換）。
    - 銘柄ごとに最大記事数・最大文字数でトリムしてバッチ（最大 20 銘柄）呼び出し。
    - JSON Mode を利用した厳密なJSON応答期待とレスポンス検証（results 配列、code/score チェック、数値の有限性）。
    - レート制限・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。
    - バリデーション失敗や API エラーはフェイルセーフとしてそのチャンクをスキップ（例外を常に上げない設計）。
    - 書き込みは ai_scores テーブルに対し、対象コードのみ DELETE → INSERT の冪等更新を行う（部分失敗時に既存データを保護）。
  - テスト用フック: _call_openai_api をパッチ差し替え可能に実装。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
  - 流れ:
    - ma200_ratio を DuckDB（prices_daily）から計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - マクロキーワードで raw_news タイトルを抽出し、OpenAI（gpt-4o-mini）により macro_sentiment をスコア化。
    - API 失敗やパース失敗は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - 再試行・エラー処理を実装（RateLimit, APIConnectionError, APITimeoutError, APIError の扱い）。
  - テスト用フック: _call_openai_api をモック可能に実装。

- データ基盤（src/kabusys/data/*）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを元に営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（土日非営業日）。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得し保存、バックフィル、健全性チェック付き）。
    - 最大探索日数やバックフィル日数などの安全パラメータを設定して無限ループや異常データを防止。
  - ETL パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを定義（取得件数、保存件数、品質問題、エラー一覧、ヘルパーは to_dict）。
    - pipeline の方針: 差分取得、idempotent 保存、品質チェック（quality モジュール）による検出を行う設計。
    - ETL 側でのバックフィルとカレンダー先読みの方針を実装。
    - 注意: etl.py の一部実装が提示コードで途切れている（将来的な修正対象）。

- 研究用機能（src/kabusys/research/*）
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン・ma200_dev）、ボラティリティ（20日 ATR・ATR比率）、流動性（20日平均売買代金・出来高比）、
      バリュー（PER, ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 計算は prices_daily と raw_financials のみを参照し、ルックアヘッドバイアスを避ける設計。
    - 十分なデータがない場合は None を返す安全設計。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応・入力検証）を実装。
    - IC（Information Coefficient）計算（Spearman の ρ）を実装（rank ユーティリティ含む）。
    - factor_summary にて基本統計（count/mean/std/min/max/median）を算出。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。

- 再利用性とテスト容易性
  - OpenAI 呼び出しや時間参照についてテスト用に差し替え可能な設計（モジュール結合を避ける）。
  - ルックアヘッドバイアス対策が一貫して適用（関数は date 引数を取り、datetime.today()/date.today() を直接参照しない箇所が多い）。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Security
- 環境変数の読み込みで OS 環境変数を保護する仕組み（protected set）を導入。自動 .env 上書きの制御で秘匿情報の意図しない上書きを防止。

### Removed / Deprecated
- なし（初回リリース）

---

署名:
- 本 CHANGELOG はリポジトリ内ソース（src/kabusys 配下）から推測して作成しました。実際のコミット履歴やリリースノートが別にある場合はそちらを優先してください。