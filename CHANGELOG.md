# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

リリース日: 2026-03-29

## [0.1.0] - 2026-03-29

### Added
- 基本パッケージ構成を追加
  - パッケージ識別子: `kabusys`（`__version__ = "0.1.0"`）。
  - 公開モジュール: data, strategy, execution, monitoring（`__all__` 定義）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは `.git` または `pyproject.toml` から探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パースの強化:
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし行のインラインコメント処理（直前が空白/タブの場合に # をコメントとみなす）。
  - 上書き制御（`.env` と `.env.local` の優先度、OS 環境変数保護）を実装。
  - 必須環境変数検証を提供（`_require`）。
  - アプリケーション設定ラッパー `Settings` を実装（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境種別・ログレベル検証、環境判定ユーティリティ）。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を用いた銘柄ごとのニュース集約 → OpenAI（gpt-4o-mini）でのセンチメントスコア付与（`score_news`）。
    - JSTベースのニュースウィンドウ計算（前日15:00〜当日08:30相当のUTC換算）を実装（`calc_news_window`）。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数/文字数トリム、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。API失敗時は部分スキップして継続。
    - DuckDB への冪等書き込み（DELETE → INSERT、トランザクション）と DuckDB executemany の空リスト回避ロジック。
    - テスト容易性のために OpenAI 呼び出し箇所を差し替え可能（`_call_openai_api` を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出（`score_regime`）。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロニュースはキーワードフィルタで抽出し、記事がなければ LLM 呼び出しをスキップ（macro_sentiment=0.0）。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 を採用、リトライ/ログ出力を実装。
    - 計算結果を `market_regime` テーブルへ冪等的にトランザクション保存。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、20 日 ATR、流動性指標（20日平均売買代金・出来高比率）を計算する関数を実装（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - DuckDB 上の SQL とウィンドウ関数で実装し、データ不足時の扱い（None）を明記。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（`calc_forward_returns`）、IC（スピアマン ρ）計算（`calc_ic`）、ランク計算（`rank`）、統計サマリー（`factor_summary`）を実装。
    - 外部依存を避け標準ライブラリのみで実装。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - 営業日判定・前後営業日の取得・期間内営業日の列挙・SQ 判定といったユーティリティを実装（`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`）。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 値優先の一貫したロジック、および探索上限（最大検索日数）を実装。
    - 夜間バッチ更新ジョブ（J-Quants からの差分取得 → 冪等保存）を実装（`calendar_update_job`）。バックフィルや健全性チェックを含む。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETL の結果を表すデータクラス `ETLResult` を実装（取得件数、保存件数、品質問題、エラー一覧など）。
    - 差分取得／バックフィル／品質チェック設計を反映したユーティリティ関数群を実装予定（パイプライン骨格を提供）。
  - ETL 再公開（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数に関するバリデーションを実装。必須環境変数が未設定の場合は明示的なエラーを発生させる（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
- ログレベル・環境種別の許容値チェックを実装（`KABUSYS_ENV`, `LOG_LEVEL` の検証）。

### Notes / Design Decisions
- ルックアヘッドバイアス防止のため、全ての「基準日」処理は datetime.today()/date.today() を内部参照しない設計。呼び出し側が target_date を明示的に渡すことを前提とする。
- OpenAI 呼び出しは JSON Mode（厳密な JSON 出力）を要求し、レスポンスの堅牢なバリデーションとパース回復処理（最外の {} を抽出）を行う。
- API 呼び出し失敗時はフェイルセーフ（0.0 やスキップ）で継続する設計。完全失敗を防ぎつつ、ログで詳細を記録する。
- DuckDB を主要なローカル分析ストアとして利用。トランザクション（BEGIN/COMMIT/ROLLBACK）と executemany の互換性に配慮した実装を行っている。
- テスト容易性のため、OpenAI 呼び出しポイントはモック差し替え可能にしている（ユニットテストでの切替を想定）。

---

今後の予定（例）
- strategy / execution モジュールの実装（売買ロジック・発注処理）および監視（monitoring）機能の追加。
- jquants_client の統合テスト・品質チェック（quality モジュール）の具体化。
- ドキュメント（API 使用例、ETL 運用手順）の拡充。

もし CHANGELOG に含めたい他の情報（例えばリリース日を別の日にする、より詳細な変更点の追加など）があれば教えてください。