# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、安定性の高いバージョニングと変更履歴の追跡を目的としています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース。国内株自動売買システムのコアライブラリを提供します。主要な機能群は設定管理、データ取り込み（ETL）、マーケットカレンダー管理、AI ベースのニュースセンチメント/市場レジーム判定、リサーチ用ファクター計算および特徴量解析ユーティリティです。設計上、ルックアヘッド（将来情報参照）を避ける実装方針と、DB書き込みの冪等性・フェイルセーフ（API失敗時は継続）を重視しています。

### Added
- パッケージ基盤
  - kabusys パッケージ（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 設定・環境変数管理 (`kabusys.config`)
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env のパース機能を実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
  - .env 読み込み時の protected キー（OS 環境変数保護）を尊重する動作。
  - 必須環境変数取得ヘルパー `_require` と Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などのプロパティ。
    - デフォルト値や型変換（Path/float）を提供（例: DUCKDB_PATH, SQLITE_PATH, CPU/MEMORY/DISK 閾値）。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）。
    - is_live / is_paper / is_dev の簡易判定プロパティ。
- AI（自然言語処理）モジュール (`kabusys.ai`)
  - news_nlp モジュール:
    - raw_news と news_symbols を用いた銘柄別ニュース集約。
    - 時間ウィンドウ計算（JST基準の前日15:00〜当日08:30相当のUTC変換）。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出す一括スコアリング（最大バッチサイズ 20 銘柄）。
    - トークン肥大化対策（1銘柄あたり最大記事数・最大文字数トリム）。
    - 再試行ポリシー（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）と失敗時のフェイルセーフ（スキップ）。
    - レスポンス検証ロジック（JSON 抽出、results 構造チェック、コード整合性、数値チェック、±1.0 でクリップ）。
    - 最終的に ai_scores テーブルへ冪等的に書き込み（該当コードのみ DELETE → INSERT）。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）の200日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出しは独立実装（モジュール間結合を避ける）。
    - LLM 呼び出しは JSON Mode を期待、再試行/エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 として継続。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時はROLLBACK）。
    - ルックアヘッド防止設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
- データプラットフォーム (`kabusys.data`)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル読み書き、営業日判定、next/prev/get_trading_days/is_sq_day 等）。
    - DB 登録がない場合は曜日ベース（週末除外）でのフォールバック。
    - calendar_update_job: J-Quants API から差分取得・バックフィル（直近再取得）・健全性チェック（過剰未来日付のスキップ）・冪等保存。
  - pipeline / etl:
    - ETLResult データクラス（取得/保存件数、品質チェック結果、エラー列挙、to_dict 変換）。
    - ETL の方針とユーティリティ（差分更新、backfill、品質チェック、idempotent save を前提）。
    - 内部ユーティリティ(テーブル存在確認、最大日付取得等)を実装。
  - jquants_client / quality 等のクライアント/補助モジュールの利用を前提（コード内で jquants_client を参照）。
- リサーチ（研究）モジュール (`kabusys.research`)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、ATR 比率）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数群:
      - calc_momentum, calc_volatility, calc_value。
    - 設計上外部 API へのアクセスは行わず、結果は (date, code) 形式の dict リストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、バリデーション付き）。
    - IC（Information Coefficient）計算（スピアマン順位相関）: calc_ic。
    - ランク付けユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）。
    - pandas 等に依存しない純標準ライブラリ実装。
- 共通設計/品質
  - ルックアヘッドバイアス回避方針を各所で採用（target_date 未満のみ参照、datetime.today() の不使用等）。
  - DuckDB を主要なローカルデータストアとして利用（クエリは SQL とウィンドウ関数を多用）。
  - DB 書き込みは可能な限り冪等性を担保（DELETE → INSERT、ON CONFLICT 想定など）。
  - OpenAI 呼び出しに関する再試行・退避・レスポンス検証の実装により外部API障害に頑強な設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。
  - 注意: OpenAI APIキーや各種トークンは Settings を通じて環境変数から読み込む設計。運用時は環境変数管理に注意してください。

### Notes / Implementation details（補足）
- OpenAI 呼び出しは gpt-4o-mini を前提に JSON Mode を利用する実装。レスポンス処理では JSON の前後ノイズを取り除く工夫をしている。
- テスト容易化のため、OpenAI 呼び出し部分（各モジュールの _call_openai_api） を unittest.mock.patch 等で差し替え可能にしている。
- DuckDB のバージョン互換性（executemany に空リストを渡せない等）を考慮した実装が散見される（ai_scores 書き込み等）。
- calendar_management のマーケットカレンダー未取得時は曜日ベースのフォールバックを行う一方、DB に登録がある場合は DB を優先する一貫した挙動を実装。

---

今後の予定（例）
- strategy / execution / monitoring の具象実装（発注ロジック・注文実行・監視ジョブ等）の追加。
- テストカバレッジ強化、CI/CD 用のワークフロー整備。
- ドキュメント（Usage / Deployment / Operation 手順）整備。

---

[0.1.0]: v0.1.0

（注）本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。