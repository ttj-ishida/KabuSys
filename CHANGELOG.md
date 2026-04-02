# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 章は可能な限り標準カテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）を使用しています。
- 日付はリリース日を示します（YYYY-MM-DD）。

## [Unreleased]

### Known issues / 修正予定
- pipeline._get_max_date の実装がソース内で途中で切れている（`return date.fro` のような不完全な行が存在）。ETL の最終取得日判定周りで例外や不正な動作を引き起こす可能性があるため、実装補完が必要。
- OpenAI を用いる AI 機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）が必須。キー未設定時は ValueError を送出する仕様のため、ランタイム環境に注意が必要。
- DuckDB のバージョン依存（executemany に空リストを渡せない等）に配慮した実装が随所にあるため、運用環境の DuckDB バージョンとの互換性確認を推奨。

---

## [0.1.0] - 2026-04-02

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring をトップレベルでエクスポート。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイル（.env / .env.local）および OS 環境変数からの自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - .env パーサーの実装: コメント行・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント処理などに対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / システム環境 (KABUSYS_ENV, LOG_LEVEL) 等の取得プロパティを定義。バリデーション（有効な env 値やログレベル）を組み込み。
  - 必須環境変数取得時に未設定なら ValueError を送出するユーティリティを提供。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を銘柄毎に集約し、最大 _BATCH_SIZE（20）ずつ OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込み。
    - 1銘柄あたり記事数・文字数のトリム処理、JSON レスポンスの堅牢なバリデーション、スコアのクリッピング、部分的書き込み（対象 code のみ DELETE → INSERT）といったフェイルセーフ実装。
    - 429 / 接続断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフのリトライ実装。
    - calc_news_window ユーティリティ（JST 時間帯ウィンドウの算出）を提供。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して market_regime テーブルへスコアとラベル（bull/neutral/bear）を冪等的に書き込み。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は安全に中立（ma200_ratio=1.0）を採用。
    - OpenAI 呼び出しは独立実装で最大リトライや 5xx の取り扱い、JSON パース失敗時のフォールバック（macro_sentiment=0.0）を行う。

- Research モジュール (kabusys.research)
  - factor_research.calc_momentum / calc_volatility / calc_value
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB クエリで計算する関数群を実装。
    - 欠損データやデータ不足時は None を返す安全設計。
  - feature_exploration.calc_forward_returns / calc_ic / rank / factor_summary
    - 将来リターン（複数ホライズン）計算、ランク相関（Spearman の ρ に基づく IC）計算、ランク化ユーティリティ、ファクター統計サマリーを提供。
    - pandas など外部ライブラリに依存しない純 Python 実装。入力検証と境界チェックを実装。

- Data モジュール (kabusys.data)
  - calendar_management
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と、JPX カレンダーを J-Quants から差分取得して更新する夜間バッチ（calendar_update_job）を実装。
    - DB データが未取得の場合は曜日ベースでフォールバックする方針、最大探索日数制限やバックフィル日数の設定などの健全性チェックを導入。
  - pipeline / etl / ETLResult
    - ETLResult データクラスを定義し、ETL 実行結果（取得件数、保存件数、品質問題、エラー概要など）を構造化して返す仕組みを追加。
    - pipeline モジュールに ETL の差分取得・保存・品質チェック方針を記載した実装。jquants_client と quality モジュール経由で Idempotent 保存と品質検査を行う設計。
  - etl モジュールは pipeline.ETLResult を再エクスポート（簡易 API）。

- その他の実装上の配慮
  - DuckDB を主要データストアとして利用する前提で SQL のウィンドウ関数や executemany 書き込み戦略を使用。DuckDB バージョン依存の問題（空リスト executemany など）に配慮した実装を行っている。
  - ロギング（情報・警告・デバッグ）を各処理に埋め込み、フェイルセーフ動作（例: API 失敗時のスコアフォールバック）を基本方針としている。
  - ルックアヘッドバイアス回避のため、日付周りの処理は内部で現在日時を参照せず、明示的な target_date を必須で受け取る設計。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

---

注記:
- 本 CHANGELOG は与えられたソースコードから推測して作成しています。実際のリリース履歴やコミットログとは差異がある可能性があります。
- 早急に対処が必要な箇所として pipeline._get_max_date の未完成実装を挙げています。ETL 周りの安定運用には修正が必須です。
- OpenAI / 外部 API を使用する機能を本番運用する場合、API キー管理・レート管理・コスト管理について十分に考慮してください。