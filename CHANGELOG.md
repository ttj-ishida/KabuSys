# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
現在のバージョン: 0.1.0

## [Unreleased]
（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装・公開。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージメタ情報を定義（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ で宣言。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（export 指定、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
  - protected（OS 環境変数）を保護して .env 上書きを制御。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能:
    - J-Quants / kabuステーション / LINE API / DBパス（DuckDB / SQLite） / 監視設定（PID/KILLフラグ） / リソース閾値（CPU/MEM/DISK） / 環境（development/paper_trading/live）/ログレベル等。
  - 必須環境変数未設定時は明示的な ValueError を送出する `_require` を実装。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を使い、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini, JSON Mode）でセンチメント解析し ai_scores テーブルへ書き込む機能を実装。
  - 時間ウィンドウ: JST 前日 15:00 〜 当日 08:30（UTC 変換：前日 06:00 〜 23:30）に対応する calc_news_window を提供。
  - バッチ処理: 最大 20 銘柄単位で API 送信（_BATCH_SIZE）。
  - トークン肥大化対策: 1銘柄あたり記事数上限・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装（最大リトライ回数、待機秒数など）。
  - レスポンス検証: JSON パース、"results" 構造、各要素の code/score 検証、スコアの ±1.0 クリップ。
  - 部分失敗対策: 成功した銘柄のみ DELETE → INSERT による置換を行い、部分失敗時に既存スコアを保護。
  - テスト容易性: _call_openai_api を patch で差し替え可能に設計。

- AI レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次書き込みを行う score_regime を実装。
  - マクロキーワードによる raw_news フィルタリング（キーワードリストを定義）。
  - OpenAI 呼び出しは JSON Mode を使い、同様にリトライ・フェイルセーフを実装。API失敗時は macro_sentiment=0.0 で継続。
  - レジームスコアの合成と閾値判定（bull / neutral / bear）。結果は DuckDB トランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等的に保存。
  - lookahead バイアス防止設計（date 比較は target_date 未満 / target_date ベースで実装）。

- データ（Data）モジュール（src/kabusys/data/）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータがない場合は曜日ベース（平日のみ営業）でフォールバックする設計。
    - 最大探索範囲・健全性チェック・バックフィル機能を実装。
    - calendar_update_job により J-Quants から差分取得 → 保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを定義し、取得数・保存数・品質問題・エラーを集約して返す仕組みを実装。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client との連携想定）。
    - ヘルパー関数: テーブル存在チェック、最大日付取得等を定義。
  - etl.py で ETLResult を再エクスポート。

- リサーチ（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を計算（duckdb SQL ベース）。
    - calc_volatility: 20日 ATR（atr_20/atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務値を取得し PER / ROE を計算。
    - データ不足時は安全に None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を用いた一括取得）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - rank: 同順位を平均ランクに変換するユーティリティ（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - research パッケージの __init__ で主要関数を再公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- API 層の堅牢性強化
  - OpenAI 呼び出しでの各種エラー（RateLimit, Connection, Timeout, APIError）の扱いを明確化し、適切にログ出力してフェイルセーフ（0.0 またはスキップ）する実装を追加。
  - DuckDB の executemany に関する互換性（空リスト不可）に対応するガード処理を追加。
  - トランザクション失敗時の ROLLBACK 失敗に対して警告ログを出すようハンドリング。

### セキュリティ (Security)
- 環境変数は protected set により OS 環境変数が誤って上書きされないよう配慮。
- OpenAI API キーは明示的に引数で注入可能（テスト容易化）かつ、未設定時は ValueError で早期に検出。

### 注意事項 / 実装ノート
- 全体設計において「ルックアヘッドバイアス防止」が厳格に採用されています。関数は datetime.today()/date.today() を直接参照せず、必ず target_date を明示的に受け取ります。
- DuckDB を主要なローカルデータストアとして使用する前提で実装されており、SQL と Python の混在で処理を行います。主要な書き込み操作は冪等（既存行の DELETE → INSERT 等）を意識しています。
- OpenAI 呼び出しは JSON 出力（厳密な JSON）を期待するプロンプト設計になっています。レスポンスパースに失敗した場合はスコア計算をスキップまたはデフォルト値へフォールバックします。
- テスト容易性のため、内部の API 呼び出しラッパー（_call_openai_api 等）は unittest.mock.patch により差し替え可能に設計されています。
- このリリースでは strategy / execution / monitoring の具体的実装ファイルは含まれていませんが、パッケージ公開インターフェースは整備済みです。

---

参照:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時は追加の運用情報（マイグレーション、既知の問題、外部 API のバージョン要件等）を追記してください。