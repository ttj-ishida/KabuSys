# Changelog

すべての主な変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

リリース日付はコードベースから推測できる最新の作業日を使用しています。

## [0.1.0] - 2026-04-04

最初の公開リリース。日本株自動売買システムのコアライブラリを提供します。以下は本バージョンで追加された主な機能と設計上の重要な点の概要です。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として公開。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイル自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - 行パーサーの強化:
    - export プレフィックス対応
    - シングル/ダブルクォートとバックスラッシュエスケープ対応
    - インラインコメント扱いのルール（クォートの有無で挙動を分ける）
  - Settings クラスを提供し、環境変数からアプリ設定を取得:
    - J-Quants, kabuステーション, LINE, DBパス (duckdb/sqlite)、監視設定（PID/KILL フラグ、閾値）などをプロパティで取得
    - 必須項目未設定時に明確なエラーメッセージを投げる `_require`
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値の検査）
    - is_live / is_paper / is_dev のヘルパー

- AI ニュース・レジーム判定 (kabusys.ai)
  - ニュースセンチメント (kabusys.ai.news_nlp)
    - raw_news + news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - JST 時間ウィンドウの計算ユーティリティ `calc_news_window(target_date)` を実装（前日15:00 JST ～ 当日08:30 JST を対象）。
    - バッチ処理: 最大 20 銘柄／コール、1銘柄あたりの最大記事数・最大文字数を制限してトークン肥大化に対応。
    - エラー耐性: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢な検証: JSON モードでも余計な前後テキストを抽出してパース、期待構造（results）・型・未知コードの無視・スコアの数値検証、±1.0 クリップ。
    - DuckDB に書き込む際の冪等性設計: 取得済みコードのみを対象に DELETE → INSERT を行い、部分失敗時に他コードの既存データを保護。
    - テスト容易性: OpenAI 呼び出し関数をモジュール内で分離して unittest.mock.patch により差し替え可能。
    - 公開 API: `score_news(conn, target_date, api_key=None)` — 書き込んだ銘柄数を返す。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算、マクロニュース抽出（キーワードベース）、OpenAI 呼出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API リトライ/エラー処理: レート制限・接続エラー・タイムアウト・5xx を考慮した再試行とフェイルセーフ（失敗時は macro_sentiment=0.0）。
    - 設計方針: ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満のデータのみ使用。
    - 公開 API: `score_regime(conn, target_date, api_key=None)` — 完了時に 1 を返す（成功指標）。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装（J-Quants から差分取得して market_calendar に冪等保存）。
    - 営業日判定/前後営業日/期間内営業日取得/ SQ 判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーが無い場合のフォールバック: 曜日ベース（土日非営業日）。
    - 安全対策: 最大探索日数 `_MAX_SEARCH_DAYS=60`、バックフィルや健全性チェック（未来の過大日付検知）を実装。

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開し、ETL 実行結果を構造化して返却可能に。
      - 取得件数、保存件数、品質問題リスト、エラーリスト、便利プロパティ（has_errors, has_quality_errors）などを提供。
      - to_dict() により品質問題を辞書化して出力可能。
    - 差分取得・バックフィル・API 取得・保存（jquants_client 経由で idempotent 保存）・品質チェックの方針を実装に反映。
    - DuckDB に関する互換性配慮（executemany に空リストを渡さない等）を仕様に組み込み。

- Research モジュール (kabusys.research)
  - ファクター計算群 (kabusys.research.factor_research)
    - Momentum: `calc_momentum(conn, target_date)` — 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を算出。データ不足時は None。
    - Volatility & Liquidity: `calc_volatility(conn, target_date)` — 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率など。
    - Value: `calc_value(conn, target_date)` — raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS が 0/欠損のとき PER は None）。
    - 設計方針: DuckDB SQL を主体に実装し、外部 API へのアクセスは行わない。結果は (date, code) をキーとする辞書リストで返却。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=None)` — 複数ホライズンをまとめて取得しリターン算出（デフォルト [1,5,21]）。
    - IC（Information Coefficient）: `calc_ic(factor_records, forward_records, factor_col, return_col)` — スピアマンのランク相関により IC を返す（有効レコード < 3 の場合は None）。
    - ランク変換ユーティリティ: `rank(values)` — 同順位は平均ランクを返す実装。
    - 統計サマリー: `factor_summary(records, columns)` — count/mean/std/min/max/median を計算する。
    - 依存最小化: pandas 等に依存せず標準ライブラリで実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし（ただし実装側で DuckDB executemany の空リスト制約や OpenAI レスポンスの不定形へのフォールバックなどの堅牢化対応を実装）。

### 既知の設計上の注意点 / 注釈
- ルックアヘッドバイアス対策:
  - AI モジュールおよびリサーチ系関数はいずれも内部で datetime.today()/date.today() を参照せず、外部から渡される target_date を基準に処理する設計です。
- OpenAI API 呼び出し:
  - gpt-4o-mini（JSON mode）を想定。API キーは引数または環境変数 `OPENAI_API_KEY` を使用。
  - テスト性向上のため OpenAI 呼出し点をモジュール内関数として分離しており、テスト時に差し替え可能。
- DB 書き込みの冪等性:
  - market_regime / ai_scores 等は既存レコードの上書き戦略（DELETE → INSERT）で部分失敗時に既存データを保護する設計。
- 環境変数の取り扱い:
  - .env のパースは比較的寛容だが、必須項目が未設定の場合は ValueError を投げて早期検出する。
  - 一部の設定（例: LOG_LEVEL, KABUSYS_ENV）は受け入れ可能な値のバリデーションを行う。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになるバージョンを考慮して、該当処理は空リストガードを入れている。

### セキュリティ (Security)
- 初回リリース時点で重大なセキュリティ修正は無し。ただし OpenAI API キー等の機密は環境変数で管理すること。

---

将来のリリースでは、戦略（strategy）や実行（execution）・監視（monitoring）周りの実装拡充、性能改善、より高度な品質検査ルールやテストカバレッジの追加などを予定しています。