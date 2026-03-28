# Keep a Changelog
このファイルは Keep a Changelog の形式に準拠しています。  
慣例に従いセマンティックバージョニングを使用します。

## Unreleased
（なし）

## [0.1.0] - 2026-03-28
初回公開リリース — 日本株自動売買支援ライブラリ "KabuSys" のベース実装。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py に v0.1.0 を設定し、主要サブパッケージ（data, research, ai, execution, monitoring）を公開。
- 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env ファイルの詳細なパース実装（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメント処理等）。
    - OS 環境変数を保護する protected override ロジック。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数検査用の `_require` と、Settings クラスを提供。プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト), SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH / SQLITE_PATH（Path 型で展開）
      - KABUSYS_ENV の検証（development, paper_trading, live）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）および is_live/is_paper/is_dev ヘルパー
- AI（ニュース/レジーム）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行う `score_news` を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ `calc_news_window` を提供。
    - バッチ処理（最大20銘柄/チャンク）、記事トリム（記事数・文字数上限）、リトライ（429・ネットワーク・5xx に対する指数バックオフ）、レスポンスバリデーション、スコア ±1.0 クリップ、ai_scores テーブルへの冪等的な書き込み（DELETE→INSERT）を実装。
    - テスト容易性のため、OpenAI 呼び出し部分は `_call_openai_api` を切り出し、patch による差し替えを想定。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース由来の LLM センチメント（重み30%）を合成して日次市場レジームを判定する `score_regime` を実装。
    - MA 計算は lookahead を防ぐため target_date 未満のデータのみ使用。データ不足時は中立（ma200_ratio=1.0）でフォールバック。
    - マクロ記事の抽出（キーワードベース）と OpenAI 呼び出し（JSON パース・リトライ・フェイルセーフ）により macro_sentiment を算出。
    - 合成スコアに基づき regime_label を決定し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しも独立した内部実装として切り出し、モジュール間の結合を避ける設計。
  - src/kabusys/ai/__init__.py で主要 API（score_news）を公開。
- データプラットフォーム
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジックを実装（market_calendar テーブル参照）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB にデータがない場合は曜日ベースでフォールバック。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants API から差分取得・バックフィル・健全性チェック・保存）。
    - 最大探索日数やバックフィル日数等の安全設計を導入（無限ループ防止 / 異常検出時スキップ）。
  - src/kabusys/data/pipeline.py
    - ETL の骨子（差分取得、保存、品質チェック）のためのユーティリティ群を実装。
    - ETL 実行結果を表す dataclass `ETLResult` を追加（品質問題のサマリーやエラーフラグ、to_dict による直列化をサポート）。
    - DuckDB 上の最大日付取得等のヘルパーを実装。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - jquants_client / quality 等のクライアント抽象を用いる想定（実際の API 呼び出しは jquants_client 経由）。
- リサーチ / ファクター
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数群を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB のウィンドウ関数を活用した実装で、データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存無しで動作する純標準ライブラリ実装。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート（zscore_normalize は data.stats から）。
- 実装上のテスト容易化・設計メモ
  - OpenAI 呼び出し箇所は直接 patch/差し替え可能な内部関数として設計（単体テストでのモックが容易）。
  - 日付取り扱いで lookahead バイアスを避けるため、datetime.today()/date.today() を直接参照しない設計（関数は target_date を引数として受け取るか、必要な場合のみ内部で date.today() を使用）。
  - DuckDB を主要なストレージとして想定（SQL を多用）。

### Fixed
- フェイルセーフ挙動を追加 / 明示化
  - OpenAI API 呼び出し失敗時は 0.0（中立）にフォールバックして処理を継続する箇所を明示（ニュース／レジーム双方）。
  - JSON パース失敗や想定外レスポンスは警告ログ出力のうえ該当チャンクをスキップし、全体の処理継続を保証。
  - DuckDB の executemany に空リストを渡せない点に配慮した空リストチェックを追加（互換性対策）。
  - market_calendar の NULL 値に対してログ警告を出し、曜日フォールバックを使用。

### Security
- 必須シークレット（OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等）は環境変数必須にし、未設定時は明確なエラーメッセージを発生させる `_require` を用意。
- .env の自動ロードはデフォルト有効だが、`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト時などに便利）。

### Notes / Implementation decisions
- 外部 API（OpenAI, J-Quants, kabu API）とのやり取りはクライアントレイヤー経由で行う想定で、各モジュールは直接の注文発行等は行わない（研究・スコアリング・ETL 層に集中）。
- 多くの処理で「部分失敗時に他データを保護する」方針（部分的なデータ書き換え防止、削除→挿入の範囲を限定）が取られている。
- ロギングを広範に配置し、運用時のトラブルシュートとリトライ状況の可視化を重視。

---

今後のリリースで予定される追加点（例）
- 発注/Execution 層の実装と paper/live モードでの統合テスト
- モデル・戦略の保存・バックテスト機能
- より詳細な品質チェックルールと監査ログ出力の強化

ご要望があれば、CHANGELOG の粒度（コミット毎 / 機能毎など）やリリースノートの英語版を作成します。