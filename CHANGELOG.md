# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買プラットフォームのコアライブラリを追加しました。主な追加点と設計上の重要事項は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期エクスポートを追加（data, research, ai, execution, monitoring を想定した __all__）。
  - バージョン情報を `__version__ = "0.1.0"` に設定。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイル（.env, .env.local）と OS 環境変数から設定を読み込む自動ロードを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）を行い、CWD に依存しない自動ロードを実現。
  - .env パーサは次の機能に対応：
    - export プレフィックス対応（`export KEY=VAL`）
    - シングル / ダブルクォート中のエスケープ処理
    - コメント（#）の扱い（クォートの有無に応じた正しいパース）
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - Settings クラスを提供し、typed プロパティ経由で各種設定を取得（J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定）。
  - 設定値バリデーション:
    - KABUSYS_ENV は `development | paper_trading | live` のみ許容
    - LOG_LEVEL は標準ログレベルのみ許容
  - デフォルトパス（duckdb, sqlite, pid/kill flag など）を指定。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ定義（JST ベース、前日 15:00 〜 当日 08:30）と UTC 変換ロジック。
  - バッチ処理と制限:
    - 1 API コールあたり最大 20 銘柄（_BATCH_SIZE=20）
    - 1銘柄あたり最大記事数 10、最大文字数 3000（トリム）
  - 安定性とフォールトトレランス:
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（最大リトライ回数）
    - API レスポンスの厳格なバリデーション（JSON パース、results 配列、コード照合、数値検証）
    - スコアは ±1.0 にクリップ
    - 部分失敗時の DB 保護: 取得できた銘柄コードのみ DELETE → INSERT で置換（既存スコアの不必要な削除を回避）
    - DuckDB の executemany の制約に配慮（空リストは実行しない）
  - テスト容易性を考慮したフック:
    - OpenAI 呼び出しを行う内部関数をモック可能（unittest.mock.patch で差し替え可能）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で regime を判定し market_regime テーブルへ保存する処理を実装。
  - 判定フロー:
    - ma200_ratio を DuckDB から計算（target_date 未満のデータのみを使用しルックアヘッドを排除）
    - raw_news からマクロキーワードで記事タイトルを抽出（最大 20 件）
    - OpenAI（gpt-4o-mini）でマクロセンチメントを JSON 出力で取得し合成
    - 合成スコアを基に 'bull' / 'neutral' / 'bear' ラベル化
    - DB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行して上位へスロー
  - フェイルセーフ: API エラーやパースエラー時は macro_sentiment = 0.0 にフォールバック（例外を投げず継続）
  - OpenAI 呼び出しはニュース NLP と独立した実装（モジュール結合を低く保つ）

- データ ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult dataclass を実装し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を一元管理。
  - 差分取得、バックフィル、品質検査を想定した設計（定数・バックフィル日数・最小データ日など）。
  - DuckDB テーブル存在チェック等のユーティリティを追加。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを利用した営業日判定ユーティリティを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供
  - DB 未取得日がある場合は曜日ベース（週末除外）でフォールバックする一貫した挙動を採用。
  - calendar_update_job を実装し J-Quants から差分取得 → idempotent に保存（バックフィルと健全性チェックを含む）。
  - 最大探索日数制限や異常検出（将来日付が過度に大きい場合はスキップ）を導入。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の計算
    - calc_value: 最新の raw_financials に基づく PER / ROE 計算
    - 設計方針として DuckDB 上の SQL と標準 Python を組み合わせて実装
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: Spearman（ランク相関）による IC 計算（3 銘柄未満は None を返す）
    - rank: 同順位を平均ランクとするランク化ユーティリティ（丸めによる ties 対策あり）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

注記（設計上の重要点）
- ルックアヘッドバイアス回避: いずれのモジュールも date.today()/datetime.today() を直接参照せず、呼び出し側が target_date を明示する設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）失敗時も全面停止させず、可能な限り安全なデフォルトや部分書き込みで進行する方針。
- テスト容易性: OpenAI 呼び出しなどは内部関数をモック可能にし、ユニットテストを行いやすい設計。
- DuckDB 互換性考慮: executemany の空リスト回避や日付の取り扱いに対する細かな互換性配慮を実装。

今後の予定（短期）
- ETL パイプライン本体の実装完了（差分取得ループ・quality モジュール統合）
- execution / monitoring パッケージの具体的な注文/監視ロジック実装
- ドキュメント（API 仕様・設計文書）の拡充
- CI 用のテストケース整備（外部 API のモックを使った統合テスト）

--- 
（この CHANGELOG はコードベースから推測して生成しています。実際のコミット履歴と差異がある場合は適宜修正してください。）