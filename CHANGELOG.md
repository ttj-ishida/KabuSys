# Changelog

すべての重要な変更はここに記録します。本プロジェクトはセマンティックバージョニングに準拠します。

フォーマットは "Keep a Changelog" に準拠しています。

※推測に基づきコードベースの実装内容から記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能と実装が含まれます。

### Added
- パッケージ初期構成を追加
  - 公開モジュール: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring をパッケージ外向けに公開。
  - パッケージバージョン: 0.1.0 を設定。

- 環境設定 / 設定管理
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - プロジェクトルート（.git または pyproject.toml）を起点に .env, .env.local を探索して読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用フック）。
  - 高度な .env パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、無効行スキップ等の挙動に対応。
    - 読み込み時の既存環境変数保護（protected set）や override 挙動をサポート。
  - Settings クラスを追加:
    - J-Quants / kabu API / Slack / DB ファイルパス / 監視しきい値 / 実行環境 (KABUSYS_ENV) / LOG_LEVEL 等のプロパティを提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効値集合チェック）と便捷プロパティ（is_live / is_paper / is_dev）。

- AI モジュール（OpenAI 統合）
  - kabusys.ai.news_nlp.score_news:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores テーブルへ保存する処理を実装。
    - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）に基づく記事抽出（UTC 変換）とバッチ処理（最大20銘柄/チャンク）。
    - スコアのバリデーション、±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフ再試行、部分成功時に既存スコアを保護する安全な DB 書き込み（DELETE → INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（モジュール内で明示的にラップ）。
  - kabusys.ai.regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等的に書き込む処理を実装。
    - マクロニュースは raw_news をマクロキーワードでフィルタして LLM に渡す。LLM 呼び出しは再試行戦略を持ち、失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - ルックアヘッドバイアスを避けるため日付の扱いと DB クエリに注意（target_date 未満のデータのみ利用等）。

- Data モジュール（データ基盤 / ETL / カレンダー）
  - calendar_management:
    - market_calendar を利用した営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースのフォールバックを行い、最大探索日数で無限ループを防止。
    - calendar_update_job により J-Quants からカレンダーを差分取得して market_calendar に冪等保存（バックフィル、健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL 実行結果・品質問題・エラー集約用）。
    - ETL パイプラインの設計（差分取得、backfill、品質チェックの統合、jquants_client 経由の idempotent 保存）を実装方針として反映。
    - データ品質チェックモジュール（quality）との連携を想定し、品質問題を収集して呼び出し元に通知できるように設計。

- Research モジュール（ファクター計算 / 特徴量探索）
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200 日 MA のデータ不足時は None、営業日ベースの窓）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算（欠損時は None）。
    - calc_value: raw_financials から最新の EPS / ROE を取得して PER / ROE を計算（EPS が 0/欠損のときは None）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を用いた1クエリ取得）。
    - calc_ic: スピアマンのランク相関（IC）を実装（レコード結合、None 除外、最小サンプルチェック）。
    - rank: 同順位は平均ランクで処理（round による ties 考慮）。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を実装。
  - research.__init__ で主要関数を再エクスポート。

### Changed
- （初回リリースのため変更履歴はなし。ただし、実装上以下方針が明示）
  - すべてのランタイム日付参照は datetime.today()/date.today() の直接参照を避け、関数引数として受け取る設計を採用（ルックアヘッドバイアス防止）。
  - OpenAI API 呼び出しは JSON mode を使用し、レスポンスの厳密なバリデーションを行うことで堅牢性を確保。

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。キー未設定時は明示的な ValueError を送出して安全性を確保。

### Notes / Implementation details / テストフレンドリーな工夫
- OpenAI 呼び出し箇所はモジュール内でラップしており、unittest.mock.patch による差し替えでテスト可能。
- .env 読み込みはプロジェクトルート探索に基づき、パッケージ配布後の CWD 依存を排除。
- DuckDB 用の SQL は互換性・性能に配慮して設計（例: executemany 空リスト回避、ROW_NUMBER を用いた最新財務レコード取得など）。
- API 呼び出し失敗時のフォールバック（中立スコア・スキップ）により、ETL/解析パイプラインの可用性を優先。

---

過不足や注記したい点があればお知らせください。さらに細かい変更点や個別ファイルごとの要約（行数や関数一覧など）も作成できます。