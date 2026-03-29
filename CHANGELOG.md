Keep a Changelog
=================

すべての重要な変更をこのファイルで記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリースは逆順（新しいものを上）で記載します。

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0"。
  - 主要サブパッケージ公開: data, research, ai, (および将来的に strategy, execution, monitoring を想定)。

- 環境設定/ロード機能 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ を起点として探索（CWD に依存しない）。
  - .env パーサーは次をサポート:
    - コメント行、空行、先頭に "export " を含む形式、
    - シングル/ダブルクォート内のバックスラッシュエスケープ、
    - クォートなしでの行内コメント（'#' の直前が空白/タブの場合のみコメントとして扱う）。
  - ロード優先順位: OS 環境変数 > .env.local > .env。OS 環境変数を保護するための protected キー処理（上書き回避）。
  - 自動ロード停止フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを公開（settings）：J-Quants / kabu / Slack / DB パス等のプロパティとバリデーション（必須 env は _require にて ValueError を送出）。
  - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の妥当性チェックと短縮判定ヘルパー（is_live 等）。

- AI 関連（src/kabusys/ai/）
  - ニュースセンチメント: news_nlp.score_news を実装
    - 前日15:00 JST ～ 当日08:30 JST のウィンドウ計算（UTC naive datetime で返す calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1銘柄あたり記事数・文字数上限でトリム）。
    - OpenAI（gpt-4o-mini）へ最大 _BATCH_SIZE (20) 件ずつ送信。JSON Mode を利用して厳密な JSON を期待。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code と score のチェック、スコアの ±1 クリップ）。
    - DuckDB への書き込みは部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT（トランザクション／冪等性）。
    - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能。
  - 市場レジーム判定: regime_detector.score_regime を実装
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して daily レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、calc_news_window と同様のウィンドウルールを使用。
    - OpenAI 呼び出しは独立実装（news_nlp と内部実装を共有しないことでモジュール結合を低減）。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - リトライ、JSON パース失敗、API ステータスハンドリング（5xx の再試行等）を実装。

- リサーチ機能（src/kabusys/research/）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離の計算を実装。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を算出。true_range を厳密に扱い NULL の伝播を制御。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 または欠損時は None）。
    - すべて DuckDB SQL を主体に実装し、本番発注 API 等にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon の将来リターンを LEAD を用いてまとめて取得。horizons のバリデーションあり。
    - calc_ic: スピアマン（ランク）相関を実装（ties は平均ランクで処理）。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクを返す安定実装（丸めで ties 判定の誤差を防止）。
    - factor_summary: count/mean/std/min/max/median を計算（None 値は除外）。
  - research パッケージは外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

- データ基盤機能（src/kabusys/data/）
  - calendar_management:
    - JPX カレンダーの管理ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - カレンダー更新ジョブ calendar_update_job: J-Quants API から差分取得、バックフィル、健全性チェック、jquants_client 経由で保存。異常・API エラー時は安全に 0 を返す。
    - 最大探索日数やバックフィル設定により無限ループを回避。
  - pipeline (ETL):
    - ETLResult dataclass を実装し公開（src/kabusys/data/etl.py で再エクスポート）。
    - 差分更新のための最終取得日取得ユーティリティ、テーブル存在チェック等を実装。
    - ETL の設計方針（差分更新、backfill、品質チェックは Fail-Fast ではなく結果回収型）を反映。
    - quality モジュールとの統合点（品質問題は ETLResult.quality_issues に収集）。

- 実装・運用上の配慮・設計判断
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を分析/スコアリング内部で直接参照しない一貫方針（全関数は target_date を引数として受け取る）。
  - DB 書き込みは冪等性を重視（DELETE → INSERT のパターン、トランザクション）
  - OpenAI API 呼び出しのエラー時フェイルセーフ（多くのケースで例外を上位に伝播させずデフォルト値で継続）と再試行戦略を採用。
  - DuckDB のバージョン依存性（例: executemany に空リストを渡せない制約）への対処が組み込まれている（空チェックを実装）。

Changed
- 初回公開のため該当なし。

Fixed
- 初期実装として以下の耐障害性改善を含む:
  - OpenAI レスポンスが前後に余計なテキストを含む場合に最外の JSON オブジェクトを抽出して復元する処理を追加（news_nlp のパース耐性向上）。
  - DuckDB executemany の空パラメータ問題に対するガードを追加（空リストの場合は実行をスキップ）。

Deprecated
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。環境変数（API キー等）は Settings 経由で必須チェック/取得する設計。

Notes / 今後の予定（暗黙的に示唆されている点）
- strategy / execution / monitoring サブパッケージの実装と統合（発注ロジック、モニタリング、運用ワークフロー）。
- テストカバレッジ強化（OpenAI など外部 API のモックを使った単体テスト）。
- J-Quants / kabu ステーションクライアントの統合テストおよび運用ドキュメント整備。

貢献・バグ報告
- バグ報告や改善提案は issue を通してお願いします。コードの設計意図やフェイルセーフ挙動については docstring を参照してください。