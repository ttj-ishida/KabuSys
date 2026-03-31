# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本リポジトリの初回公開リリースとして以下の履歴を作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買／データ基盤・研究用ユーティリティのコア実装を追加。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名とバージョンを定義（__version__ = "0.1.0"）。
    - public API のエクスポート一覧（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（優先度: OS 環境 > .env.local > .env）。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD 非依存で自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - export KEY=val 形式・クォート・コメント対応を含む堅牢な .env パーサー実装。
    - 環境変数未設定時に ValueError を投げる _require() と Settings クラスを提供。
    - 各種設定プロパティ（J-Quants / kabuAPI / Slack / DB パス / 環境モード / ログレベル 判定ユーティリティ）。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事から銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む処理を実装。
    - JST 時間ウィンドウ（前日15:00〜当日08:30）を UTC に変換して対象記事を収集する calc_news_window 関数。
    - 記事集約、長さトリム（記事数上限 / 文字数上限）、チャンク（最大20銘柄）での OpenAI バッチ呼び出し。
    - JSON Mode を想定したレスポンス検証（厳密な JSON 期待。前後の余計なテキストが混入しても削り取りを試みる）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
    - レスポンスバリデーションで未知コードや非数値を除外、スコアは ±1.0 にクリップ。
    - 部分失敗に配慮した DB 書き込み（対象コードのみ DELETE → INSERT）とトランザクション処理。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）をサポート。未設定時は ValueError。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（Nikkei225 連動 ETF）の200日移動平均乖離（重み70%）と
      マクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッド回避）。データ不足時は中立 (1.0)。
    - マクロニュース抽出（キーワードリストに基づくタイトルフィルタリング、最大 20 記事）。
    - OpenAI 呼び出しは独立実装。API エラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 合成スコアのクリップとラベリング、market_regime テーブルへの冪等的書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー注入サポート（引数 or OPENAI_API_KEY）、未設定時は ValueError。

- データ / ETL / カレンダー系
  - src/kabusys/data/pipeline.py
    - ETLResult データクラス実装。ETL の取得数・保存数・品質問題・エラー一覧を保持・シリアライズ可能。
    - 差分取得用ユーティリティ（テーブルの最大日付取得等）。
    - 市場カレンダーのヘルパー（営業日調整関数など）を提供。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート（公開インターフェース）。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の夜間バッチ更新処理 calendar_update_job を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジック。
    - DB データ優先・未登録日は曜日ベースでフォールバック。探索範囲上限で無限ループ防止。
    - J-Quants クライアント経由で差分フェッチ→冪等保存。バックフィル期間や安全チェック（将来日付の異常検出）を実装。

  - src/kabusys/data/__init__.py
    - data パッケージの土台（クライアントやユーティリティを統合する想定）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 等の定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
      - calc_value: raw_financials を参照して PER（EPS が 0 または欠損時は None）、ROE を算出。
    - DuckDB SQL を活用した実装で、外部 API にアクセスせずオフラインで計算可能。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応・入力検証）。
    - calc_ic: スピアマンランク相関（Information Coefficient）をコード結合して計算（有効レコードが3未満の場合は None）。
    - rank: 平均ランク付け（タイの処理は平均ランク）。
    - factor_summary: count/mean/std/min/max/median の統計概要を算出。
    - 依存を標準ライブラリと DuckDB のみとして研究用途で使いやすく設計。

- 公開 API 再配布
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py により主要関数を __all__ で公開。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数の自動読み込みで OS 環境を上書きしないデフォルト挙動（.env の override=False）。.env.local は override=True。
- 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

### Notes / Known limitations / Design decisions
- OpenAI 連携は gpt-4o-mini を前提に JSON Mode で動作する設計。API レスポンスの不整合や API キー未設定時にはフェイルセーフ（スコア=0 や処理スキップ）を採る。
- DuckDB に依存する設計（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等のテーブル構造を前提）。
- 日付取り扱いはルックアヘッドバイアス回避のため、内部で date.today() / datetime.today() を参照しない方針（target_date を明示的に渡す必要がある）。
- news_nlp と regime_detector は内部で OpenAI 呼び出し関数を独立実装しており、テスト時に差し替え（unittest.mock.patch）できるように設計。
- 一部 DuckDB の executemany に関する互換性（空リスト渡し不可）を考慮した実装を行っている。

---

著者: KabuSys 開発チーム  
（リリースノートはコードベースの実装内容から推測して作成しています。実際の運用・API 仕様・DB スキーマはドキュメントを参照してください。）