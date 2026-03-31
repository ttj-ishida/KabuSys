# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

- リリースポリシー: メジャー.マイナー.パッチ のセマンティックバージョニングを想定。
- 日付はコードベースの最新版に合わせて推測しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを導入。公開 API として data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を順に読み込み。
    - .env.local は .env の上書き（override）を行う。
    - OS 環境変数を保護する仕組み（protected keys）を組み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーを強化:
    - export KEY=val 形式、シングル/ダブルクォートやバックスラッシュエスケープ、行末コメント処理に対応。
  - 必須設定取得用の _require()、環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - 各種設定プロパティを提供（J-Quants / kabu API / Slack / DB パス / 監視閾値など）。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出する score_news を実装。
    - ニュースウィンドウ（JST 前日15:00～当日08:30）を UTC に変換する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり最大記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行を実装。
    - レスポンスの厳密な JSON バリデーションとスコアの ±1.0 クリッピング、部分成功時の DB 書き込み（DELETE→INSERT）での原子性と既存データ保護。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（モジュール内部の _call_openai_api をモック可能）。
  - kabusys.ai.regime_detector:
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily から MA200 乖離を算出する処理、raw_news からマクロキーワードでタイトル抽出、OpenAI（gpt-4o-mini）コール、リトライ/フォールバック（API失敗時 macro_sentiment=0.0）を実装。
    - レジーム結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - モジュール間の結合を避ける設計（news_nlp の内部関数を直接共有しない）。

- 研究（Research）モジュール
  - ファクター計算群を実装（kabusys.research）:
    - calc_momentum: 1M/3M/6M リターンと MA200 偏差を計算（営業日ベース）。
    - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を用いた PER/ROE 計算（target_date 以前の最新財務データを利用）。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一度の SQL で取得する汎用実装。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。
    - rank: 同順位は平均ランクを与えるランク変換ユーティリティ（浮動小数点の丸め処理を考慮）。
    - factor_summary: カウント/平均/標準偏差/最小/最大/中央値を計算する統計サマリ。

- データ（Data）プラットフォーム
  - calendar_management:
    - JPX カレンダーの管理（market_calendar）用ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・保存を行うロジックを実装（健全性チェック・バックフィル・lookahead パラメータを考慮）。
    - DB にデータがない場合は曜日ベース（平日のみ営業日）でフォールバックする一貫した振る舞い。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラーメッセージの収集）。
    - ETL 実行に関する設計方針と差分更新／品質チェックの骨格を実装。
    - _table_exists / _get_max_date 等のユーティリティ関数（DuckDB 互換の注意点を考慮）。
  - jquants_client との連携を想定した差分取得・保存ロジックの骨組み。

- 実装上の設計方針（全体）
  - ルックアヘッドバイアス回避: 各モジュール（news/regime/research）は datetime.today() / date.today() を参照しない方針で、必ず caller が target_date を渡す設計。
  - DuckDB 互換性やバインドの制約（executemany と空リストの扱い等）を考慮した実装。
  - API 呼び出し周りは再試行とフェイルセーフ（失敗時はスキップ・0.0 フォールバック等）で堅牢性を高める。
  - ロギングを広範に実装し、失敗時には警告/例外ログで追跡しやすくしている。

### 変更 (Changed)
- 初期リリースのため当該バージョンでの互換性変更はなし（新規実装）。

### 修正 (Fixed)
- 初期リリースのため既存のバグ修正履歴はなし。

### 既知の問題 / 注意事項 (Known issues / Notes)
- 一部ファイルがコードスニペットで途中切れ・未完成の可能性:
  - pipeline._get_max_date の末尾が途切れているように見える（date.fro といった不完全な記述）。ビルド前に該当箇所の確認と修正が必要。
- data/__init__.py は空でエクスポートの整理が未実装の可能性あり。
- OpenAI API の利用には OPENAI_API_KEY の設定が必須。テスト時は各モジュールの _call_openai_api をモックすることが想定されている。
- DuckDB のバージョン差異により配列バインディングや executemany の挙動が異なる点に注意（実運用では対象バージョンでの検証必須）。
- news_nlp の JSON 出力は LLM の挙動によって逸脱する場合があるため、レスポンス復元ロジック（最外の {} を抽出する等）を組み込んでいるが、完全保証はない。

---

もし CHANGELOG をリポジトリのコミット履歴や実際のリリース日に合わせて更新したい場合、現状のコード断片から推定した内容をベースに追加情報（実際のリリース日・マイナーな修正点・テスト結果）を提供してください。必要なら英語版や短縮版も作成できます。