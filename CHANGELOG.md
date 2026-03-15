# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

現在のフォーマットに従い、主要なリリースは下記に記載します。

<!-- このファイルはコードベースの現状（スキャフォールド）から推測して作成しています。 -->

## [Unreleased]

## [0.1.0] - 2026-03-15
### 追加
- 初期リリース: 日本株自動売買システム用のパッケージ `kabusys` を追加。
  - パッケージのトップレベル説明（docstring）を追加: "KabuSys - 日本株自動売買システム"。
  - バージョン情報を定義: `__version__ = "0.1.0"`。
  - パッケージ公開 API を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
  - 以下のモジュール／サブパッケージ構成を作成（ファイルはプレースホルダとして空の __init__.py を含む）:
    - `kabusys.data` — データ取得・管理用（スキャフォールド）
    - `kabusys.strategy` — 売買戦略定義用（スキャフォールド）
    - `kabusys.execution` — 注文発注・実行用（スキャフォールド）
    - `kabusys.monitoring` — 監視・ログ・状態監視用（スキャフォールド）
- プロジェクトのソース配置:
  - `src/kabusys/__init__.py`
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`

### 注意
- 現在のコミットは主にパッケージ構造（スキャフォールド）および公開 API の定義に焦点を当てた初期設定です。各サブパッケージには実装が含まれておらず、今後のリリースで機能追加・実装が行われる予定です。

---

（以降のリリースはここに追記します。）