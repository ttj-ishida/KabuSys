# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を公開します。

### 追加 (Added)
- パッケージ初期化
  - パッケージのバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める（__all__）。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートの検出（.git または pyproject.toml を基準）に基づく .env / .env.local の自動読み込み。
    - OS 環境変数を保護する protected セットをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いの実装。
  - Settings に主要設定プロパティを用意（J-Quants、kabuステーション、Slack、DB パス、監視閾値、環境・ログレベルの検証等）。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをバッチで OpenAI（gpt-4o-mini）に送信し ai_scores テーブルへ書き込み。
    - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30 相当）計算ユーティリティ（calc_news_window）。
    - バッチ処理（最大20銘柄）、1銘柄あたりの記事数・文字数上限（トリム）を実装。
    - レスポンスの JSON パースとバリデーション（results 配列、code/score の型チェック、スコアのクリップ）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ付きリトライ。
    - API 呼び出しはテストで差し替え可能（_call_openai_api をモック可能）。
    - Fail-safe 動作: API 失敗やパースエラー時は該当チャンクをスキップし、他の処理を継続。
    - DuckDB 用の冪等な書き込みロジック（DELETE → INSERT、executemany 空リスト回避）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と
      マクロニュースの LLM センチメント（重み30%）を合成し市場レジーム（bull/neutral/bear）を日次判定。
    - MA200 比率計算、マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し（JSON mode）、
      再試行・フォールバックロジック、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - Look-ahead バイアス防止のため、target_date 未満のデータのみ使用する設計。

- データ管理モジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定、次/前営業日の検索、期間内営業日の取得、SQ 日判定を提供。
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日）を採用。
    - カレンダー夜間バッチ更新ジョブ（calendar_update_job）を追加（J-Quants API 経由で差分取得、バックフィル、健全性チェック実装）。
  - ETL パイプライン（pipeline）
    - ETLResult dataclass を公開（取得・保存件数、品質問題、エラーの集約）。
    - 差分取得、idempotent 保存、品質チェックの統合を想定した設計。jquants_client / quality 統合ポイントを用意。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチモジュール（kabusys.research）
  - ファクター計算（research.factor_research）
    - モメンタム：1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - ボラティリティ／流動性：20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等。
    - バリュー：PER（EPS が 0/欠損なら None）、ROE（raw_financials から取得）。
    - DuckDB を用いた SQL を主体とする実装。欠損時は None を返す方針。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの将来終値からリターンを計算（複数ホライズン対応）。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装（3 銘柄未満は None）。
    - ランク変換ユーティリティ（rank）：同順位時は平均ランクを割り当てる。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算（None 除外）。

### 変更 (Changed)
- 初回公開のため履歴なし（本バージョンが初出）。

### 修正 (Fixed)
- 初回公開のため履歴なし。

### 注意事項 / 既知の制約 (Known limitations)
- DuckDB 依存:
  - 実装は DuckDB の SQL 表現・挙動に依存している（例: executemany の空リスト制約、ROW_NUMBER/ウィンドウ挙動等）。
  - consumers は期待されるテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）を用意する必要があります。
- OpenAI 呼び出し:
  - gpt-4o-mini の JSON Mode を前提に実装しているため、API や SDK の変更に対して注意が必要です。
  - OpenAI API 呼出しはネットワーク障害やレート制限を考慮したリトライを行うが、最終フォールバックではスコアを 0.0（中立）にするなどの挙動をとります。
- 時刻/日付の扱い:
  - すべての関数はルックアヘッドバイアスを避けるために datetime.today() / date.today() を内部で参照しない設計です（target_date を明示的に渡すこと）。
  - news ウィンドウは JST を基準に定義し、DB との比較は UTC naive datetime を用いる実装になっています。利用時は DB に格納された datetime が UTC 前提であることを確認してください。
- テストのしやすさ:
  - OpenAI 呼び出しは内部関数（各モジュールの _call_openai_api）をパッチすることでモック可能。ユニットテストを容易にする設計。

### 必要な環境変数（利用時の注意）
- JQUANTS_REFRESH_TOKEN（J-Quants API）
- KABU_API_PASSWORD（kabuステーション）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack通知）
- OPENAI_API_KEY（AI 機能を使用する場合）
- 各種パス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）は Settings のデフォルトを使用可能

### 開発者向けメモ
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを抑制可能。
- OpenAI 関連のユニットテストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch してレスポンスをエミュレートしてください。
- DuckDB による SQL 実行で日付/型の取り扱いに若干の差異が出る場合があるため、テスト環境でのスキーマ確認を推奨します。

---

今後の予定（例）
- strategy / execution / monitoring の具体的な実装追加（発注ロジック、監視エージェント等）。
- API クライアント（jquants_client）や品質チェック（quality）モジュールの実装拡充。
- CI テスト、エンドツーエンド検証の整備。

（以上）