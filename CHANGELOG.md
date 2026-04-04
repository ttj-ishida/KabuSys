# Changelog

全ての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトのバージョンはパッケージヘッダで定義された __version__ = 0.1.0 です。

以下はコードベースから推測して作成したリリースノート（日本語）です。

## [Unreleased]

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ骨組みを追加
  - パッケージルート: `kabusys`（__init__ にて version と公開サブパッケージを定義）。

- 環境設定・自動 .env ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装を追加（コメント行、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応）。
  - 上書き挙動:
    - `.env` は OS 環境変数を保護して未設定キーのみ設定。
    - `.env.local` は `.env` の上から上書き（ただし既存の OS 環境変数は保護）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / 環境種別（development/paper_trading/live）などの設定値をプロパティとして取得可能。
  - 必須環境変数未設定時は明示的に ValueError を送出（例: OpenAI キーや各種 API トークンは呼び出し時にチェック）。

- AI 関連機能（kabusys.ai）
  - news_nlp モジュール（score_news）:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini の JSON Mode）へバッチ送信して銘柄ごとのセンチメントスコアを算出。
    - バッチサイズ、記事数上限、文字数トリム、スコアクリップ（±1.0）等の安全策を導入。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンスバリデーション処理を実装（JSON 抽出、results リスト検査、未知コードは無視）。
    - DuckDB への置換書き込みは部分失敗に備えて該当コードのみ DELETE→INSERT（executemany を使用し互換性を考慮）。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として公開。
    - テストで OpenAI 呼び出しを差し替えられるよう内部呼び出し関数を分離（unittest.mock.patch を想定）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。API キー未提供時は ValueError。
  - regime_detector モジュール（score_regime）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、news_nlp のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはタイトルベースでマクロキーワードにマッチしたものを抽出し、OpenAI（gpt-4o-mini）へ送信して JSON スコアを取得。
    - API のリトライ・フェイルセーフ（API 故障時は macro_sentiment=0.0）やレスポンスパース失敗のハンドリングを実装。
    - レジームは計算後 DuckDB の market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行し、失敗ログを出力して例外を再送出。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1 を返す。API キー未提供時は ValueError。

- リサーチ（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）および流動性指標の計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、営業日バッファやデータ不足時の None ハンドリング、結果を (date, code) ベースの dict リストで返す。
    - 公開関数: calc_momentum, calc_value, calc_volatility。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの将来終値からリターンを算出。horizons の検証と一度のクエリで複数ホライズンを取得する実装。
    - IC（Information Coefficient）計算（calc_ic）: factor と forward の結合、スピアマンランク相関（ランクは同順位の平均ランク）を実装。有効レコードが 3 未満の場合 None を返す。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - ユーティリティ: rank（丸めによる ties 処理）、factor_summary 等。
    - 研究向け API を __all__ で再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダーの管理・夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（保存は jquants_client 側で idempotent な実装を想定）。
    - 営業日判定ユーティリティを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - カレンダーが未取得の場合は曜日ベースのフォールバック（土日を休日扱い）。DB 登録値が優先され、未登録日はフォールバックで一貫して補完する設計。
    - 探索上限（日数）を設定して無限ループを防止。バックフィル日数や先読み日数、健全性チェック（過度に未来の日付はスキップ）を導入。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl が再エクスポート）。
    - ETL フロー方針、差分更新・backfill・品質チェック（quality モジュール）との連携、J-Quants クライアント経由での保存・品質収集のための基盤実装を準備。
    - DuckDB テーブル存在確認や最大日付取得などユーティリティを実装（pipeline 内）。

- モジュール設計上の注意点（ドキュメント注釈）
  - ルックアヘッドバイアス防止: いずれのスコア計算・ウィンドウ計算も内部で datetime.today()/date.today() を直接参照しない（ターゲット日を明示的に受け取る設計）。
  - フェイルセーフ: 外部 API 失敗時は例外を投げずにスコアをスキップ・フォールバックする/0.0 を返す等の施策を採用し、バッチ処理の継続性を確保。
  - テスト容易性: OpenAI 呼び出しなどをラップして差し替え可能にしており、ユニットテストでのモックが容易。
  - DuckDB 互換性配慮: executemany の空リスト問題など特定 DuckDB バージョンの挙動に対する回避ロジックを実装。

### 変更 (Changed)
- 初回公開のため該当なし。

### 修正 (Fixed)
- 初回公開のため該当なし。

### セキュリティ (Security)
- 初回公開のため該当なし。
- 注意: OpenAI / 各種トークンは環境変数で管理する設計（Settings で取得）。コード中での平文ハードコードはない想定。

---

注記:
- 上記はリポジトリ内の docstring・実装・定数名・API シグネチャから推測して作成した CHANGELOG です。実際のリリースノートとして採用する際は、実際のコミットや CHANGELOG ポリシーに基づき適宜編集してください。