# Changelog

すべての重要な変更点を記録します。これは Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/kabusys 配下）の実装内容から推測して作成しています。

- フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買プラットフォームの基盤となる主要コンポーネントを実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0, エクスポートモジュール定義）。
- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動読み込みの探索はパッケクトルート（.git または pyproject.toml）を起点とし、CWD に依存しない実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ: export 付き行、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート。
  - Settings クラス: 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境・ログレベル判定等）。
  - 必須環境変数取得時のエラー提示（_require）。
- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を作成。
    - タイムウィンドウ定義（前日15:00 JST〜当日08:30 JST の UTC への変換）。
    - バッチサイズ、最大記事/文字数制限、JSON レスポンス検証、スコアの ±1 クリップ。
    - リトライ（429, ネットワーク, タイムアウト, 5xx）と指数バックオフの実装。
    - DuckDB の executemany に関する互換性回避（空リストバインド回避）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出・保存。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、JSON パース、再試行・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - look-ahead バイアス回避：prices_daily クエリで target_date 未満のデータのみ使用し、モジュール内で date.today() に依存しない設計。
- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を参照した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未登録日は曜日ベースのフォールバック（週末除外）。
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）と J-Quants クライアント統合、バックフィル、健全性チェック。
  - ETL パイプライン基盤（kabusys.data.pipeline / k abusys.data.etl）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧など）。
    - 差分取得・保存・品質チェックの設計方針とユーティリティ（テーブル存在確認、最大日付取得など）。
    - デフォルトのバックフィル/ルックアヘッド値・エラー／品質判定の定義。
- 研究/リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20 日）等の実装。
    - Volatility / Liquidity 指標（atr_20, atr_pct, avg_turnover, volume_ratio）。
    - Value 指標（PER, ROE を raw_financials と株価から算出）。
    - DuckDB 上で SQL とウィンドウ関数を活用した実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（スピアマン順位相関）。
    - rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）等の統計ユーティリティ。
    - pandas 等に依存しない、標準ライブラリベースの実装。

### Changed
- （初版のため変更履歴はなし。実装上の設計方針として以下を採用）
  - ルックアヘッドバイアス回避：AI モジュール・ETL・リサーチ関数は内部で date.today() を使わず、呼び出し側から target_date を明示的に渡す設計。
  - API 呼び出しはフェイルセーフ設計：外部 API（OpenAI / J-Quants）失敗時に例外を直接伝播させず、可能な限りフォールバック（0 スコア・スキップ等）して処理継続する。

### Fixed
- （初版のため「修正」はなし。ただし実装で回避している既知の問題点を明記）
  - DuckDB executemany の空リスト問題に対する回避（空パラメータを渡さないよう明示的チェックを追加）。
  - OpenAI レスポンスの JSON パースで余計な前後テキストが混入するケースに対する復元ロジックを実装（最外の {} を抽出して再パース）。

### Security
- 明示的なセキュリティ修正はなし。
- 環境変数や API キーの取り扱い:
  - OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出して明示する。
  - .env 自動読み込み時、既存の OS 環境変数は保護（protected set）して上書きを防止。

### Notes / Known limitations
- OpenAI 関連は gpt-4o-mini（JSON Mode）を使用する設計。ただし実際の API 互換性や将来の SDK 変更により適宜調整が必要。
- ai_scores / market_regime など DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を保つ実装。ただし部分失敗時の運用ルールは呼び出し側で考慮する必要がある。
- 一部の計算（MA200 等）は必要データ行数が不足する場合に None や中立値（1.0 等）を返すことで安全側に倒す設計になっています。
- 外部クライアント（jquants_client 等）は別モジュールとして期待しており、本CHANGELOGはそれらの実装依存を前提に記載しています。

---

今後のリリースでは、API クライアント実装の拡充、監視・実行部分（execution, monitoring）の詳細、テストカバレッジ増強、ドキュメント追記（使用例、運用手順）を予定しています。