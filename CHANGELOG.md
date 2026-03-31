# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

※バージョンはパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加（Added）
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート済みモジュール: data, strategy, execution, monitoring

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装
    - 読み込み優先順: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装
  - .env パーサーは export 付き行、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応
  - 環境変数取得ユーティリティ（Settings）を提供
    - J-Quants、kabuステーション、Slack、DBパス、監視閾値、実行環境（development/paper_trading/live）などをプロパティで取得
    - 必須変数未設定時は ValueError を投げる
    - LOG_LEVEL / KABUSYS_ENV の値検証を実装

- AI 関連機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を基に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメントを算出
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数上限の導入（トークン制御）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - レスポンス検証（JSONパース復元、results 配列・型・既知コード・数値チェック）、スコアは ±1.0 にクリップ
    - DuckDB の executemany 空リスト問題に対応（empty check）
    - ルックアヘッドバイアス対策: datetime.today() を直接参照しない、UTC ナイーブな時間ウィンドウ計算を提供（calc_news_window）
    - フェイルセーフ: API失敗時はスキップして処理継続（例外を波及させない）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて daily な市場レジーム（bull/neutral/bear）を判定
    - マクロセンチメントは OpenAI により -1.0〜1.0 で出力させ、JSON を厳密にパース
    - API のリトライ、5xx 判定、失敗時の macro_sentiment=0.0 フォールバックを実装
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う
    - ルックアヘッドバイアス防止の設計（prices_daily は target_date 未満のみ使用）

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER・ROE）等を DuckDB 上の SQL で効率的に計算
    - データ不足時の None 扱い、営業日ベースの horizon 設計、ログ出力
  - 特徴量探索・評価（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman ランク相関）計算（欠損除外、必要件数チェック）
    - ランキング（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）
    - pandas 等外部依存を避け、標準ライブラリ + DuckDB で実装

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装（J-Quants API 経由）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - DB 存在時は DB 値を優先、未登録日は曜日ベースでフォールバックする一貫性ある実装
    - 最大探索日数上限や健全性チェックを導入
  - ETL パイプライン / 結果型（kabusys.data.pipeline, kabusys.data.etl）
    - 差分フェッチ、idempotent な保存（ON CONFLICT 相当）、品質チェック（quality モジュール）等を想定した ETLResult データクラスを公開
    - デフォルトのバックフィルやカレンダー先読み等、運用を考慮した設計方針を採用
  - jquants_client 用ユーティリティと保存処理（jquants_client は別モジュールとして想定）

### 変更（Changed）
- （初回リリースのため履歴なし）

### 修正（Fixed）
- （初回リリースのため履歴なし）

### セキュリティ（Security）
- （該当なし）

-----

注記（設計上の重要ポイント）
- ルックアヘッドバイアス防止: いずれのスコアリング・リサーチ処理も datetime.today()/date.today() を直接参照せず、引数として渡された target_date を基準に処理する設計を採用。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は可能な限り処理を継続する（デフォルトスコア・スキップ・ログ出力）よう実装。
- DuckDB 互換性: executemany の空リスト問題や日付型の変換など、DuckDB の既知の挙動に配慮した実装を行っている。
- 環境変数の自動ロードは配布後も安全に動作するようプロジェクトルート探索を行い、OS 環境変数を保護する仕組みを含む。

もし特定モジュールのリリースノートや追加で注記が必要であれば、対象モジュール名をお知らせください。