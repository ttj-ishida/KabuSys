Keep a Changelog
=================

すべての重要な変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- なし

0.1.0 — 2026-04-04
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ公開情報
    - src/kabusys/__init__.py にてバージョン "0.1.0" と公開 API (`data`, `strategy`, `execution`, `monitoring`) を設定。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイル自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準に行う）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
    - export KEY=val 形式やクォート・エスケープ、インラインコメント等に対応した堅牢な .env パーサを実装。
    - _require による必須環境変数チェック（未設定時は ValueError）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境 / ログレベル 等）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live, is_paper, is_dev）。

- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（ai_score）を計算・ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST に対応する UTC 範囲）を calc_news_window で提供。
    - バッチ処理（1 API コールで最大 20 銘柄）・1銘柄あたりの最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ実装（最大リトライ回数・基底待機時間を定義）。
    - OpenAI レスポンス検証ロジック（JSON パース、results キー/型/スコア数値チェック、未知コードの無視、スコアの ±1.0 クリップ）を実装。
    - 部分失敗時のデータ保護のため、書き込みは対象コードに限定して DELETE → INSERT を行う（DuckDB の executemany 空リスト制約を考慮）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュースの LLM マクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等保存する機能を提供。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のみ使用）と、マクロ記事フィルタ（キーワードリスト）取得機能を実装。
    - OpenAI 呼び出しは独立実装（news_nlp の内部関数を共有しない設計）で、API 失敗時は macro_sentiment=0.0 とするフェイルセーフを採用。
    - レジームスコア合成、ラベリング、DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック時の安全処理を実装。

  - 共通設計上の注意点
    - 両モジュールとも OpenAI の API キーは引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げる明確な挙動。
    - テスト容易性のため、OpenAI 呼び出し部分は差し替え可能（モジュール内の _call_openai_api をパッチ）。

- データ管理 / ETL / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由で差分取得 → 冪等保存）。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。DB 登録がない場合は曜日ベースでフォールバック（週末除外）。
    - 最大探索日数や健全性チェック、バックフィル仕様を実装して誤った未来日付や API の訂正に対応。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETLResult データクラスで ETL 実行結果を集約（取得数・保存数・品質問題・エラーの一覧化）。
    - ETL パイプラインの設計方針とユーティリティ（差分更新、バックフィル、品質チェックの扱い等）を実装するための基盤コードを追加。
    - jquants_client を介した取得/保存処理と quality チェックとの連携を想定（実装側での idempotent 保存やエラー集約方針を反映）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン, 200 日移動平均乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金、出来高比）およびバリュー（PER, ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足や条件未達成時は None を返す扱い（安全設計）。
    - SQL ウィンドウ関数を多用し、効率的に一括計算する実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、および統計サマリー（factor_summary）を実装。
    - 外部依存（pandas 等）を使わず純 Python と DuckDB のみで実装。入力検証や数値の有限性チェック、最小サンプル数要件（IC 計算は有効レコード 3 件以上）などを実装。

- 内部・運用ユーティリティ
  - DuckDB を主要なデータストアとして想定した SQL 実行コードと互換性考慮（空の executemany 回避等）。
  - ロギングと警告出力を各モジュールで適切に出力（情報/警告/例外ログ）。
  - ルックアヘッドバイアス防止のため、いずれのモジュールも内部で date.today()/datetime.today() を直接利用せず、target_date を明示的に受け取る設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- 環境変数管理の改善により、API キー等の必須値の未設定を早期に検出（_require）し、明確なエラーを返す実装を追加。

Notes / 備考
- OpenAI の利用に関する設定や API キーの管理は本パッケージ外（環境設定／シークレット管理）で行ってください。
- DuckDB のバインド挙動（executemany の空リスト不可など）を考慮した実装を行っています。アップグレード時に互換性の差異が出る可能性があります。
- 実行環境・本番運用ではログレベル、監視閾値、DB パス等を環境変数で調整してください（config.Settings 経由で取得）。

今後の予定（参考）
- strategy / execution モジュールの公開インターフェース実装（発注ロジック・バックテスト機能等）。
- jquants_client の具体的な実装・テスト用フェイククライアントの提供。
- モデル・プロンプト改善、LLM 呼び出しのメトリクス収集と監視ダッシュボード連携。