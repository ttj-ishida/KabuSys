# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
リリースポリシー: ここに記載の v0.1.0 が初回公開リリースです（スナップショットに基づき推測して作成）。

## [Unreleased]
- （現時点で未発表の変更はありません）

## [0.1.0] - 2026-04-09
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを追加。

### Added
- パッケージ初期化
  - kabusys パッケージの基本エントリを追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - パッケージ公開 API に data, strategy, execution, monitoring を含む。

- 環境設定 / ロード
  - 環境変数管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み機能を実装。
    - .env, .env.local の読み込み順序（OS環境変数 > .env.local > .env）と上書き保護（protected keys）を実装。
    - export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などを考慮した .env パーサ実装。
    - 自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 設定取得用 Settings クラスを提供（J-Quants / kabu station / LINE / DB / 監視 / システム設定など）。
    - PAPER_FILL_MODE の値検証、KABUSYS_ENV / LOG_LEVEL のバリデーション、パス型設定（duckdb/sqlite/paper sqlite/pid/kill flag）を実装。

- AI ニュース NLP モジュール
  - ニュースセンチメント解析モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と DuckDB からの記事集約（news_symbols 結合）。
    - 銘柄単位で記事を結合し、チャンク（最大 20 銘柄）単位で API 呼び出し。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検証、コード照合、スコア数値化、±1.0 クリップ）。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時はスキップして継続するフェイルセーフ。
    - 書き込みは冪等（DELETE → INSERT）で ai_scores テーブルへ反映。部分失敗時に既存データを保護。
    - テスト時に OpenAI 呼び出しを差し替えられるよう実装（内部の _call_openai_api をモック可能）。

  - AI ユーティリティ公開（src/kabusys/ai/__init__.py）に score_news を追加。

- 市場レジーム判定モジュール
  - regime_detector を追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース（LLM センチメント、重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - DuckDB の prices_daily, raw_news, market_regime テーブルを使用。
    - OpenAI 呼び出しは独立実装でリトライ/フォールバック（失敗時 macro_sentiment=0.0）。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。

- Data モジュール（市場データ ETL / カレンダー）
  - ETL パイプラインインターフェースを追加（src/kabusys/data/etl.py / pipeline.py）。
    - ETLResult dataclass により ETL 実行結果（取得数 / 保存数 / 品質問題 / エラー）を保持・辞書化可能。
    - 差分更新・バックフィル・品質チェックを考慮した設計（jquants_client 経由の保存、品質問題は集約して返す方針）。
  - マーケットカレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - market_calendar を利用した営業日判定、next/prev_trading_day、get_trading_days、is_sq_day の実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を除外）。
    - カレンダー夜間バッチ更新ジョブ（calendar_update_job）を提供。J-Quants から差分取得・バックフィル・健全性チェックを実装。
    - 最大探索日数やバックフィル長、異常検出閾値などの安全策を導入。

- Research（因子・特徴量探索）
  - research パッケージ公開（src/kabusys/research/__init__.py）。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M, ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）の計算関数を実装。
    - DuckDB SQL ウィンドウ関数を活用し、データ不足時は None を返す設計。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン、LEAD を用いた単一クエリでの取得）。
    - IC（Spearman の ρ）計算、ランク変換（平均ランクの ties 処理）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

- その他
  - DuckDB を主なローカル DB 層として想定した実装と SQL クエリを多数追加。
  - OpenAI Python SDK で起こりうる各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対するハンドリングを導入。
  - ロギングを広範囲に導入し、情報 / 警告 / 例外の追跡を容易に。

### Changed
- 初回リリースのため該当なし（新規導入が主要変更）。

### Fixed
- 初回リリースのため該当なし。

### Security
- API キーやパスワードは環境変数から取得する設計（Settings を通して取得）。.env 自動ロードは明示的に無効化できるフラグを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 設計上のポイント
- ルックアヘッドバイアス対策: 各 AI / リサーチ処理は内部で datetime.today()/date.today() を参照せず、呼び出し側から target_date を受け取る設計。
- DB 書き込みは可能な限り冪等に（DELETE → INSERT または ON CONFLICT 相当）保護されている。
- API 呼び出しはリトライ＋フォールバックを採用し、致命的な失敗でプロセスを停止させない（部分失敗の保護）。
- テスト容易性: OpenAI 呼び出し等は関数レベルで差し替え可能に実装。

### Known issues / Limitations
- 外部 API クライアント（jquants_client 等）や strategy / execution / monitoring の具体実装は本スナップショットで省略または別モジュールに依存（本CHANGELOGは提供コードから推測して作成）。
- OpenAI のレスポンスフォーマットに依存しているため、将来のモデルや SDK の変更に合わせた調整が必要になる可能性あり。

---

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴や PR／issue の記載を基に調整してください。