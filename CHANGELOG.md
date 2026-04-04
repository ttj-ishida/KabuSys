# CHANGELOG

すべての重要な変更は「Keep a Changelog」準拠で記載しています。  
このログはコードベースから推測して作成した初期リリースの要約です。

なお日付はパッケージ版記載の __version__（0.1.0）と現行日付を基にしています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-04
初回リリース。本バージョンでは日本株自動売買プラットフォームの基礎となる以下の機能群を実装しています。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを定義（data, strategy, execution, monitoring を __all__ で公開）。
  - パッケージバージョン: 0.1.0

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込みを自動化（プロジェクトルート判定: .git / pyproject.toml を探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーで次をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなし行のインラインコメント判定（直前がスペース/タブ場合のみ）
  - 環境設定を一元化する Settings クラスを提供（J-Quants・kabuステーション・LINE・DBパス・監視閾値・環境種別・ログレベル等）。
  - 必須項目未設定時は ValueError を発生させる _require を実装。

- AI（自然言語）モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理: 最大 20 銘柄／リクエスト、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - JSON Mode を想定したレスポンスバリデーション（results 配列、code/score 構造の検証）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ実装（最大リトライ回数指定）。
    - スコアは ±1.0 にクリップ。部分成功時にも既存スコアを消さない（対象コードのみ DELETE → INSERT）。
    - 時間ウィンドウ計算ユーティリティ calc_news_window を提供（JST 基準の前日 15:00 ～ 当日 08:30 に対応）。
    - API 呼び出し部は差し替え可能に実装（テストでモック可能）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（タイトル抽出・JSON パース・リトライ・フォールバック実装）。
    - ルックアヘッドバイアス防止設計（date 未満のデータのみ利用、datetime.today() を参照しない）。
    - idempotent な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。API 失敗時は macro_sentiment=0.0 で継続。

- データ基盤（kabusys.data）
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルの読み書き、営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未登録の期間は曜日ベース（土日除外）でフォールバックする堅牢設計。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装：J-Quants クライアント経由で差分取得 → 冪等保存、バックフィル、健全性チェック等を実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラー集約などを保持）。
    - pipeline モジュールの ETLResult を kabusys.data.etl 経由で再エクスポート。
    - 差分更新やバックフィル、品質チェックを想定した設計ドキュメントに沿った構成（実装内での説明あり）。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム: mom_1m / mom_3m / mom_6m、200 日 MA 乖離を計算（データ不足時は None）。
    - ボラティリティ／流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（ウィンドウ不足時は None）。
    - バリュー: PER（EPS が 0/欠損なら None）、ROE（raw_financials を利用）を計算。
    - DuckDB を用いた SQL + Python 実装、外部 API へはアクセスしない設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）まで一括で計算、引数検証あり。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関を実装し、データ不足時は None を返す。
    - ランク変換（rank）：同順位は平均ランクで処理（丸めで ties 検出の安定化）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 注意事項 / 設計上の制約
- OpenAI API キーは api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出。
- DuckDB の executemany に対する実装上の互換性（空リストを渡さない等）に配慮したコードになっています。
- 多くの処理で「ルックアヘッドバイアス防止」のため現在時刻を直接参照しない設計になっており、テスト容易性と再現性を重視しています。
- 外部 API（J-Quants、OpenAI）呼び出し部は例外処理とフォールバック（ゼロスコアやスキップ）を実装し、部分失敗時もシステム全体の停止を防ぐ設計です。

---

今後のリリースでは、strategy / execution / monitoring 等の取引実行まわりや監視機能の詳細実装、ドキュメント・型注釈の拡充、テストケースの追加などが想定されます。必要であれば、この CHANGELOG の英文版やコミット単位の変更要約も作成します。