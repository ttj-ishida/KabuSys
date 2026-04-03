# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョン: 0.1.0

注: 以下は提供されたコードベースの内容および docstring から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-03
初回公開リリース。金融データ取得・ETL・特徴量計算・研究用ユーティリティ・AI ベースのニュースセンチメント/市場レジーム判定など、アルゴリズム開発とデータ基盤のための主要コンポーネントを含む最小実装を提供します。

### Added
- パッケージ基礎
  - パッケージメタ情報と公開 API を定義（kabusys.__init__、バージョン "0.1.0"）。
  - モジュール群のエクスポート: data, research, ai, research のエントリポイントを整備。

- 設定・環境変数管理（kabusys.config）
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env および .env.local ファイルの自動読み込み（読み込み順: OS 環境変数 ＞ .env.local ＞ .env）。
  - 読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パーサ: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - 上書き制御: override と protected（OS 環境変数保護）をサポート。
  - Settings クラスを導入し、主要な設定をプロパティ経由で取得（J-Quants トークン、kabu API、LINE API トークン、DB パス、監視閾値など）。
  - 設定のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- データ基盤（kabusys.data）
  - ETL 基盤とユーティリティ
    - ETLResult データクラス（pipeline と etl で利用）を公開（kabusys.data.etl / pipeline）。
    - pipeline/etl モジュールにより差分取得、バックフィル、品質チェックを行う設計（J-Quants クライアント連携を想定）。
    - DuckDB を想定した実装（テーブル存在チェック、最大日付取得、executemany の空リスト回避などの互換性配慮）。
  - マーケットカレンダー管理（calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未登録時は曜日ベースでフォールバックする堅牢なロジック。
    - 最大探索日数やバックフィル日数、健全性チェックを導入して安全性を確保。
    - jquants_client 経由のフェッチ/保存を想定（差分取得/冪等保存）。

- 研究（research）モジュール
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高比）、バリュー（PER、ROE）を算出する関数群:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB SQL による実装で、prices_daily / raw_financials のみ参照（本番注文 API にはアクセスしない設計）。
  - feature_exploration
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)
    - IC（Spearman の ρ）計算: calc_ic(...)
    - ランク変換ユーティリティ: rank(values)
    - 統計サマリー: factor_summary(records, columns)
    - 標準ライブラリのみで実装（pandas などに非依存）。

- AI（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols を集約して銘柄ごとの記事をまとめ、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算（calc_news_window）。
    - バッチサイズ、1 銘柄当たりの最大記事数/文字数制限、JSON Mode 応答のバリデーション、レスポンスパースのリカバリ（余計な前後テキストの {} 抽出）を備える。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実施。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
  - regime_detector
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装（score_regime）。
    - マクロ記事抽出、OpenAI 呼び出し、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）を備え、LLM 呼び出しはモジュール固有実装で結合を避ける設計。
    - レジームスコア算出・閾値判定（BULL/BEAR閾値）を実装。
    - DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- API キーやシークレットは環境変数から取得する設計（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。  
- .env 自動ロード機構は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。  
- .env 読み込み時に OS 環境変数を protected として上書き保護するオプションを利用。

### 注意事項 / 実装上の設計決定（ドキュメント的注記）
- ルックアヘッドバイアス防止:
  - AI スコアやレジーム判定・ETL・研究用関数はいずれも内部で datetime.today() / date.today() を参照せず、外部から与えられた target_date を基準に処理することで将来情報の漏洩を防止。
  - prices_daily などのクエリは target_date 未満または target_date を基準にしてルックアヘッドを避ける条件が明示的にある。
- フェイルセーフ:
  - OpenAI API 呼び出しの失敗時は（多くのケースで）例外を投げずフォールバック値を採用して処理継続する方針（部分失敗を許容し全体処理を継続）。
- DB 書き込みの冪等性:
  - market_regime や ai_scores 等への書き込みは、既存行削除→挿入のパターンや ON CONFLICT による冪等保存を想定して実装。
- DuckDB 互換性配慮:
  - executemany に空リストを渡さないチェック等、実運用で見られる DuckDB バージョン差異を考慮した実装あり。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数をモック差し替え可能にして単体テストを容易にしている。

---

変更や不具合の報告、改善提案、API 使用上の疑問点は issue を立ててください。